#!/usr/bin/env python3
"""Finite, strict synthetic USB collector; hardware lifecycle belongs to caller.

No firmware loading, reset, restoration or USB discovery occurs here. The caller
passes its already-held lifecycle flock descriptor; this module never acquires,
unlocks or closes that descriptor. Raw captures and nonce remain in backups/.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import struct
import time
import zlib

REPO = Path(__file__).resolve().parents[1]
PENDING_FINALIZATION = '.scratch/forgix-spi-finalization-pending.json'
FRAME_BYTES, PAYLOAD_BYTES = 512, 460
RATES = (65536, 262144, 786432)
PRODUCT = "Forgix USB RAM diagnostic v1"
PROFILE = "FORGIX_USB_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56"
HEADER = struct.Struct("<4sHHIIIQ16sI")
STATS = struct.Struct("<6I5Q")
COUNTERS = ("generated", "enqueued", "discarded", "partial_write_calls", "queue_high_water", "cdc_accepted_bytes", "stalled_loop_us")


class CaptureError(RuntimeError):
    pass


def reject_pending_finalization(root):
    """Any pending-marker presence blocks all new Forgix access/recovery."""
    if os.path.lexists(Path(root)/PENDING_FINALIZATION):
        raise ValueError('Unresolved register finalization blocks device access')


def start_command(rate, nonce):
    if rate not in RATES or len(nonce) != 16 or nonce == bytes(16):
        raise CaptureError("START requires an allowed rate and a fresh nonzero nonce")
    prefix = struct.pack("<4sHHI16s", b"FRAM", 1, 1, rate, nonce)
    return prefix + struct.pack("<I", zlib.crc32(prefix))


class Decoder:
    """Keep every byte, fail at the first damaged frame, never resynchronize."""
    def __init__(self):
        self.pending = bytearray()
        self.byte_offset = 0

    def feed(self, data):
        self.pending.extend(data)

    def next_frame(self):
        if len(self.pending) < FRAME_BYTES:
            return None
        raw = bytes(self.pending[:FRAME_BYTES])
        magic, version, kind, seq, length, plen, us, nonce, flags = HEADER.unpack_from(raw)
        if (magic, version, length, plen, flags) != (b"FRAM", 1, 512, 460, 0) or kind not in range(5):
            raise CaptureError(f"Invalid framing at retained byte offset {self.byte_offset}")
        if zlib.crc32(raw[:508]) != struct.unpack_from("<I", raw, 508)[0]:
            raise CaptureError(f"CRC mismatch at retained byte offset {self.byte_offset}")
        del self.pending[:FRAME_BYTES]
        self.byte_offset += FRAME_BYTES
        return {"type": kind, "sequence": seq, "device_us": us, "nonce": nonce, "payload": raw[48:508]}

    def finish(self):
        if self.pending:
            raise CaptureError(f"Truncated record: {len(self.pending)} retained bytes")


class Validator:
    def __init__(self, source_sha256, rate, nonce):
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise CaptureError("Expected committed source-set SHA256 is invalid")
        start_command(rate, nonce)
        self.source_sha256, self.rate, self.nonce = source_sha256, rate, nonce
        self.state, self.previous_sequence, self.previous_us = "config", -1, -1
        self.counts, self.gaps, self.controls = Counter(), [], []
        self.data_bytes, self.data_arrivals_ns, self.data_device_us = 0, [], []
        self.ready_host_ns = self.end_host_ns = None
        self.boot_us = self.start_us = None
        self.loss_accounted = False

    def control(self, frame):
        p = frame["payload"]
        values = STATS.unpack_from(p)
        fields = ("rate", "generated", "enqueued", "discarded", "partial_write_calls", "queue_high_water", "cdc_accepted_bytes", "stalled_loop_us", "boot_us", "start_us", "max_lifetime_us")
        out = dict(zip(fields, values))
        profile = PROFILE.encode() + b"\0"
        if p[64:128] != self.source_sha256.encode() or p[128:128+len(profile)] != profile or any(p[128+len(profile):]):
            raise CaptureError("Control record build/profile/padding does not match reviewed artifact")
        if out["generated"] != frame["sequence"] + 1 or out["generated"] != out["enqueued"] + out["discarded"] + 1:
            raise CaptureError("Control counters do not follow pre-enqueue snapshot semantics")
        if out["queue_high_water"] > 16 or out["max_lifetime_us"] != 120000000:
            raise CaptureError("Control queue/lifetime is outside reviewed profile")
        if out["cdc_accepted_bytes"] > out["enqueued"] * FRAME_BYTES:
            raise CaptureError("CDC accepted bytes exceed already enqueued records")
        out["queued_records_before_control"] = out["enqueued"] - out["cdc_accepted_bytes"] // FRAME_BYTES
        if out["queued_records_before_control"] > 15 or out["queued_records_before_control"] > out["queue_high_water"]:
            raise CaptureError("Control queue backlog is inconsistent with enqueue/CDC counters")
        if out["boot_us"] > frame["device_us"] or out["stalled_loop_us"] > frame["device_us"] - out["boot_us"]:
            raise CaptureError("Control boot/stall epoch is impossible")
        if frame["device_us"] - out["boot_us"] >= 120000000:
            raise CaptureError("Record exceeds independent device lifetime")
        if self.controls:
            old = self.controls[-1]["counters"]
            if any(out[k] < old[k] for k in COUNTERS):
                raise CaptureError("Control counters decreased")
            if out["boot_us"] != self.boot_us:
                raise CaptureError("Device boot epoch changed")
        self.controls.append({"type": frame["type"], "sequence": frame["sequence"], "device_us": frame["device_us"], "counters": out})
        return out

    def accept(self, frame, host_ns):
        kind, seq, us = frame["type"], frame["sequence"], frame["device_us"]
        if self.state == "ended":
            raise CaptureError("Record appeared after END")
        if seq <= self.previous_sequence or us < self.previous_us:
            raise CaptureError("Sequence or device timestamp went backwards")
        if seq != self.previous_sequence + 1:
            self.gaps.append({"first": self.previous_sequence + 1, "last": seq - 1, "count": seq-self.previous_sequence-1})
        if self.state == "config":
            if kind != 0 or seq != 0 or frame["nonce"] != bytes(16):
                raise CaptureError("First record must be zero-nonce CONFIG sequence zero")
            c = self.control(frame)
            if c["rate"] or c["start_us"] or c["discarded"] or c["enqueued"]:
                raise CaptureError("CONFIG already contains a producer run")
            self.boot_us, self.state = c["boot_us"], "start_required"
        else:
            if frame["nonce"] != self.nonce:
                raise CaptureError("Record nonce does not bind this run")
            if self.state == "start_required":
                raise CaptureError("Record appeared before host START")
            if self.state == "ready":
                if kind != 1 or seq != 1:
                    raise CaptureError("READY must immediately follow CONFIG and START")
                c = self.control(frame)
                self.start_us = c["start_us"]
                if not self.start_us or us != self.start_us or self.start_us-self.boot_us >= 30000000:
                    raise CaptureError("READY START epoch is outside reviewed command window")
                self.ready_host_ns, self.state = host_ns, "data"
            elif kind == 2:
                expected = bytes(((seq*131+i*17)^self.nonce[i % 16]) & 255 for i in range(PAYLOAD_BYTES))
                if frame["payload"] != expected:
                    raise CaptureError("Deterministic DATA payload mismatch")
                if not 0 <= us-self.start_us < 60000000:
                    raise CaptureError("DATA is outside the finite producer epoch")
                self.data_bytes += PAYLOAD_BYTES
                self.data_arrivals_ns.append(host_ns)
                self.data_device_us.append(us)
                c = None
            elif kind in (3, 4):
                c = self.control(frame)
                elapsed = us-self.start_us
                if kind == 3 and not 0 <= elapsed < 60000000:
                    raise CaptureError("STATS is outside the finite producer epoch")
                if kind == 4:
                    if not 60000000 <= elapsed < 62000000:
                        raise CaptureError("END did not follow a full 60-second run within device drain grace")
                    self.end_host_ns, self.state = host_ns, "ended"
            else:
                raise CaptureError("Unexpected CONFIG or READY within run")
            if c is not None:
                if c["rate"] != self.rate or c["start_us"] != self.start_us:
                    raise CaptureError("Control requested rate or START epoch changed")
        self.counts[kind] += 1
        self.previous_sequence, self.previous_us = seq, us

    def mark_start(self):
        if self.state != "start_required":
            raise CaptureError("START may be sent once, after validated CONFIG")
        self.state = "ready"

    def finish(self):
        if self.state != "ended" or not self.data_bytes:
            raise CaptureError("Run lacks a valid END or DATA")
        end = self.controls[-1]["counters"]
        received = sum(self.counts.values())
        missing = sum(g["count"] for g in self.gaps)
        if missing != end["discarded"] or received != end["enqueued"] + 1:
            raise CaptureError("END counters do not reconcile received records and retained sequence gaps")
        if end["generated"] != received + missing:
            raise CaptureError("END generated records do not reconcile")
        self.loss_accounted = True

    def summary(self):
        intervals = [(b-a)/1e9 for a, b in zip(self.data_arrivals_ns, self.data_arrivals_ns[1:])]
        host_seconds = None if self.end_host_ns is None else (self.end_host_ns-self.ready_host_ns)/1e9
        ordered = sorted(intervals)
        distribution = {"count": len(ordered)}
        if ordered:
            distribution.update({"min_s": ordered[0], "p50_s": ordered[int((len(ordered)-1)*.5)], "p95_s": ordered[int((len(ordered)-1)*.95)], "p99_s": ordered[int((len(ordered)-1)*.99)], "max_s": ordered[-1]})
        deltas = [{"from_sequence": a["sequence"], "to_sequence": b["sequence"],
                   "device_interval_s": (b["device_us"]-a["device_us"])/1e6,
                   **{k: b["counters"][k]-a["counters"][k] for k in COUNTERS}}
                  for a,b in zip(self.controls, self.controls[1:])]
        missing = sum(g["count"] for g in self.gaps)
        no_loss = missing == 0 if self.loss_accounted else None
        return {"received_types": {str(k): v for k,v in self.counts.items()}, "verified_data_payload_bytes": self.data_bytes,
                "host_ready_to_end_s": host_seconds, "host_payload_Bps": self.data_bytes/host_seconds if host_seconds else None,
                "device_start_to_end_s": (self.previous_us-self.start_us)/1e6 if self.state == "ended" else None,
                "host_data_first_to_last_s": (self.data_arrivals_ns[-1]-self.data_arrivals_ns[0])/1e9 if self.data_arrivals_ns else None,
                "sequence_gaps": self.gaps, "data_interarrival": distribution, "control_snapshots": self.controls,
                "sampled_queue_backlog_records": [c["counters"]["queued_records_before_control"] for c in self.controls],
                "control_counter_deltas": deltas,
                "loss_accounted": self.loss_accounted, "verified_no_record_loss": no_loss,
                "loss_result": "no_record_loss" if no_loss is True else "device_discards_accounted" if self.loss_accounted else "unresolved",
                "missing_sequence_records": missing,
                "cdc_accepted_bytes_are_host_delivery": False}


def inherited_operator_lock(fd, path):
    """Inspect Linux's inherited flock receipt without acquiring a second lock."""
    path = Path(path)
    reject_pending_finalization(path.parent.parent)
    if path.is_symlink():
        raise CaptureError("Lifecycle lock path cannot be a symlink")
    path = path.resolve(strict=True)
    actual, expected = os.fstat(fd), path.stat()
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino) or not stat.S_ISREG(actual.st_mode):
        raise CaptureError("Inherited operator lock descriptor does not match lifecycle lock path")
    if actual.st_uid != os.getuid() or stat.S_IMODE(actual.st_mode) != 0o600:
        raise CaptureError("Lifecycle lock must be private and owned by current operator")
    info = Path(f"/proc/self/fdinfo/{fd}").read_text()
    if not re.search(r"^lock:\s+\S+\s+FLOCK\s+ADVISORY\s+WRITE\s+", info, re.M):
        raise CaptureError("Descriptor has no inherited exclusive lifecycle flock")
    return {"ownership": "inherited lifecycle descriptor; collector did not acquire, unlock or close it", "fd": fd}


def select_diagnostic(topology, port, sys_root=Path("/sys"), require_character=True):
    reject_pending_finalization(REPO)
    if topology != "3-3":
        raise CaptureError("This reviewed trial is restricted to explicit USB topology 3-3")
    usb = (sys_root / "bus/usb/devices" / topology).resolve(strict=True)
    read = lambda name: (usb/name).read_text().strip()
    if read("idVendor").lower() != "cafe" or read("idProduct").lower() != "4011" or read("product") != PRODUCT:
        raise CaptureError("Selected USB topology is not the distinct reviewed RAM diagnostic")
    port = Path(port).resolve(strict=True)
    if not re.fullmatch(r"ttyACM[0-9]+", port.name):
        raise CaptureError("Explicit diagnostic port must resolve to a CDC ACM tty")
    if require_character and not stat.S_ISCHR(port.stat().st_mode):
        raise CaptureError("Explicit serial port is not a character device")
    tty_device = (sys_root / "class/tty" / port.name / "device").resolve(strict=True)
    usb_ancestors = [p for p in (tty_device, *tty_device.parents) if (p/"idVendor").exists()]
    if not usb_ancestors or usb_ancestors[0] != usb:
        raise CaptureError("Explicit tty does not belong exactly to selected diagnostic USB node")
    return {"port": str(port), "usb_node": str(usb), "bus": read("busnum"), "enumeration": read("devnum"), "vid": "cafe", "pid": "4011", "product": PRODUCT, "topology": topology}


class PrivateCapture:
    def __init__(self, path, root):
        lexical_root = Path(os.path.abspath(root))
        lexical_path = Path(os.path.abspath(path))
        if lexical_root.is_symlink() or not lexical_path.is_relative_to(lexical_root):
            raise CaptureError("Private capture root and child paths cannot redirect through symlinks")
        current = lexical_path
        while current != lexical_root:
            if current.is_symlink():
                raise CaptureError("Private capture path contains a symlink")
            current = current.parent
        self.path = lexical_path.resolve()
        root = lexical_root.resolve(strict=True)
        if self.path == root or not self.path.is_relative_to(root):
            raise CaptureError("Capture must be a fresh child of ignored backups/")
        self.path.mkdir(mode=0o700)
        os.chmod(self.path, 0o700)

    def open(self, name):
        return os.fdopen(os.open(self.path/name, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600), "wb")

    def write(self, name, data):
        with self.open(name) as stream:
            stream.write(data)


def collect(store, source_sha256, rate, nonce, serial_factory, identity_check,
            lock_check, clock=time.monotonic_ns, sleep=time.sleep):
    """One run, with injectable transport/clock for real parser synthetic tests."""
    validator, decoder = Validator(source_sha256, rate, nonce), Decoder()
    serial = None
    began = clock()
    deadline = began + 85000000000
    pause = None
    error = None
    end_grace = None
    received_bytes = 0
    manifest = {"kind": "private synthetic MCU USB capture", "requested_payload_Bps": rate,
                "build_source_sha256": source_sha256, "profile": PROFILE, "host_deadline_s": 85,
                "planned_read_pause": {"after_READY_s": 30, "duration_s": .1},
                "status": "incomplete", "host_receipt_timing": "monotonic_ns after each read; batched frames share arrival"}
    store.write("nonce.bin", nonce)
    def within_deadline(stage):
        if clock() >= deadline:
            raise CaptureError(f"85-second host deadline exceeded {stage}")
    try:
        manifest["operator_lock"] = lock_check()
        manifest["identity_private"] = identity_check()
        within_deadline("before exclusive serial open")
        with store.open("raw.bin") as raw, store.open("receipts.jsonl") as receipts:
            serial = serial_factory(manifest["identity_private"]["port"])
            if identity_check() != manifest["identity_private"]:
                raise CaptureError("Diagnostic enumeration changed across exclusive serial open")
            within_deadline("during exclusive serial open/identity check")
            while clock() < deadline:
                now = clock()
                if end_grace is not None and now >= end_grace:
                    break
                if validator.state == "config" and now-began >= 20000000000:
                    raise CaptureError("CONFIG startup exceeded 20-second allowance")
                if validator.ready_host_ns is not None and pause is None and now-validator.ready_host_ns >= 30000000000:
                    before = clock()
                    sleep(.1)
                    pause = {"started_after_READY_s": (before-validator.ready_host_ns)/1e9, "actual_duration_s": (clock()-before)/1e9}
                    within_deadline("during planned read pause")
                try:
                    data = serial.read(8192)
                except OSError:
                    within_deadline("during read exception")
                    if validator.state == "ended":
                        manifest["disconnect_during_device_grace"] = True
                        break
                    raise
                arrived = clock()
                if not data:
                    if arrived >= deadline:
                        raise CaptureError("85-second host deadline exceeded")
                    continue
                offset = received_bytes
                received_bytes += len(data)
                raw.write(data)
                raw.flush()
                receipts.write((json.dumps({"offset": offset, "length": len(data), "host_elapsed_ns": arrived-began})+"\n").encode())
                decoder.feed(data)
                if arrived >= deadline:
                    raise CaptureError("85-second host deadline exceeded; late read retained")
                if validator.state == "config" and arrived-began >= 20000000000:
                    raise CaptureError("CONFIG startup exceeded 20-second allowance; late read retained")
                while (frame := decoder.next_frame()) is not None:
                    validator.accept(frame, arrived)
                    within_deadline("during frame parsing/validation; raw prefix retained")
                    if frame["type"] == 0:
                        if decoder.pending:
                            raise CaptureError("Unexpected bytes preceded host START")
                        command = start_command(rate, nonce)
                        if clock()-began >= 20000000000:
                            raise CaptureError("CONFIG validation exceeded 20-second allowance; START refused")
                        if clock() >= deadline:
                            raise CaptureError("Host deadline expired before START; command refused")
                        manifest["START_write_attempt_host_elapsed_s"] = (clock()-began)/1e9
                        sent = serial.write(command)
                        manifest["START_write_return_bytes"] = sent
                        if sent != len(command):
                            raise CaptureError("START write was incomplete")
                        validator.mark_start()
                        manifest["START_host_elapsed_s"] = (clock()-began)/1e9
                        within_deadline("during START write")
                    if frame["type"] == 4:
                        end_grace = arrived + 2000000000
            else:
                raise CaptureError("85-second host deadline exceeded without bounded completion")
            within_deadline("before final validation")
            decoder.finish()
            within_deadline("during final framing validation")
            validator.finish()
            within_deadline("during final counter reconciliation")
            if pause is None:
                raise CaptureError("Required explicit 100 ms host-read pause was not performed")
            manifest["status"] = "complete_integrity_verified"
    except BaseException as exc:
        error = exc
        manifest["status"] = "cancelled" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
        manifest["error_type"] = type(exc).__name__
        # Avoid serial exception text that may contain private host/device paths.
        manifest["error"] = str(exc) if isinstance(exc, CaptureError) else "Transport, cancellation or capture I/O failure; raw prefix retained"
    finally:
        if serial is not None:
            try:
                serial.close()
            except BaseException as exc:
                error = error or exc
                manifest["status"] = "failed"
                manifest["close_error"] = type(exc).__name__
        manifest.update(validator.summary())
        manifest["actual_read_pause"] = pause
        manifest["host_received_bytes"] = received_bytes
        # Re-read the closed file: failed flush/write may have saved only a prefix.
        try:
            saved_hash, saved_bytes = hashlib.sha256(), 0
            with (store.path/"raw.bin").open("rb") as saved:
                while chunk := saved.read(1024*1024):
                    saved_hash.update(chunk)
                    saved_bytes += len(chunk)
            manifest["raw_bytes"] = saved_bytes
            manifest["raw_sha256"] = saved_hash.hexdigest()
            manifest["raw_persistence_verified"] = True
            manifest["raw_saved_matches_received_length"] = saved_bytes == received_bytes
            if saved_bytes != received_bytes:
                error = error or CaptureError("Saved raw prefix does not contain every received byte")
                manifest["status"] = "failed"
        except OSError:
            manifest["raw_persistence_verified"] = False
            error = error or CaptureError("Saved raw prefix could not be independently read and hashed")
            manifest["status"] = "failed"
        if clock() >= deadline:
            error = error or CaptureError("85-second host deadline exceeded during close/persistence verification")
            manifest["status"] = "failed" if manifest["status"] != "cancelled" else "cancelled"
            manifest["host_deadline_exceeded"] = True
        if error is not None and "error_type" not in manifest:
            manifest["error_type"] = type(error).__name__
            manifest["error"] = str(error) if isinstance(error, CaptureError) else "Capture cleanup or persistence failure"
        manifest["actual_host_operation_s"] = (clock()-began)/1e9
        manifest["unparsed_prefix_bytes"] = len(decoder.pending)
        manifest["crc_verified_frames"] = decoder.byte_offset // FRAME_BYTES
        manifest["deterministic_payload_verified_frames"] = validator.counts[2]
        store.write("manifest.json", (json.dumps(manifest, indent=2)+"\n").encode())
    if error:
        raise error
    return manifest


def open_retaining_serial(port):
    """Keep CONFIG even if it arrives during the POSIX serial open.

    Locked pyserial 3.5 asserts DTR before its implicit input flush. The
    producer announces CONFIG once on DTR, so that flush can erase the only
    announcement. Preserve the entire prefix instead; unexpected/stale bytes
    must fail the strict decoder, never disappear through a flush or retry.
    """
    reject_pending_finalization(REPO)
    import serial

    class RetainingSerial(serial.Serial):
        def _reset_input_buffer(self):
            # Includes the implicit flush in Serial.open(). No input discard.
            pass

    return RetainingSerial(port, baudrate=115200, timeout=.05,
                           write_timeout=1, exclusive=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--usb-topology", required=True, choices=["3-3"])
    p.add_argument("--port", required=True)
    p.add_argument("--operator-lock-fd", required=True, type=int)
    p.add_argument("--operator-lock-path", required=True, type=Path)
    p.add_argument("--build-source-sha256", required=True)
    p.add_argument("--rate", required=True, type=int, choices=RATES)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    reject_pending_finalization(REPO)
    def cancel(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, cancel)
    store = PrivateCapture(args.output, REPO/"backups")
    try:
        result = collect(store, args.build_source_sha256, args.rate, secrets.token_bytes(16), open_retaining_serial,
                         lambda: select_diagnostic(args.usb_topology, args.port),
                         lambda: inherited_operator_lock(args.operator_lock_fd, args.operator_lock_path))
    except (CaptureError, OSError, KeyboardInterrupt):
        p.exit(1, "Capture failed or cancelled; private manifest/raw prefix retained. Lifecycle owner must verify return.\n")
    print(json.dumps({"status": result["status"], "verified_data_payload_bytes": result["verified_data_payload_bytes"],
                      "loss_result": result["loss_result"], "verified_no_record_loss": result["verified_no_record_loss"]}))


if __name__ == "__main__":
    main()
