#!/usr/bin/env python3
"""Preserve an explicitly identified factory Forgix; never load, erase or write OTP.

Run from the Nix shell. --help does not inspect or open hardware. Raw transcripts
and two full-flash reads stay in a fresh directory below ignored backups/.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import time
import uuid
import zlib


REPO = Path(__file__).resolve().parents[1]
FACTORY_PID = "0009"
BOOT_PID = "000f"
HEADER = struct.Struct("<4sBBHIII")


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class PreservationError(RuntimeError):
    pass


class PrivateStore:
    def __init__(self, path, allowed_root):
        self.path = Path(path).resolve()
        root = Path(allowed_root).resolve()
        if self.path == root or not self.path.is_relative_to(root):
            raise PreservationError("Private directory must be a new child of backups/")
        if not self.path.parent.is_dir():
            raise PreservationError("Create the parent backup directory first")
        self.path.mkdir(mode=0o700)  # Existing directories, including symlinks, fail.
        os.chmod(self.path, 0o700)

    def create(self, name, data=b""):
        if Path(name).name != name:
            raise PreservationError("Private file name must be a basename")
        path = self.path / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        return path

    def json(self, name, record):
        return self.create(name, (json.dumps(record, indent=2) + "\n").encode())


@dataclass(frozen=True)
class USBTarget:
    topology: str
    bus: int
    address: int
    pid: str
    node: str
    serial_sha256: str = ""


class Inspector:
    def __init__(self, topology, serial_port, sys_root=Path("/sys"), dev_root=Path("/dev")):
        if not re.fullmatch(r"[0-9]+-[0-9]+(?:\.[0-9]+)*", topology):
            raise PreservationError("Select a physical USB topology, not an interface or wildcard")
        self.topology = topology
        self.port = Path(serial_port)
        self.sys_root = Path(sys_root)
        self.dev_root = Path(dev_root)
        self.identity_hash = None

    @property
    def usb_path(self):
        return self.sys_root / "bus/usb/devices" / self.topology

    def target(self, pid, bus=None):
        path = self.usb_path
        read = lambda name: (path / name).read_text().strip()
        if read("idVendor").lower() != "2e8a" or read("idProduct").lower() != pid:
            raise PreservationError("Selected USB topology has the wrong VID/PID")
        serial = read("serial").casefold()
        if not serial or serial in ("0", "unknown", "none"):
            raise PreservationError("USB unique identity is missing; preservation reset refused")
        identity_hash = sha256(serial.encode())
        if self.identity_hash is None:
            if pid != FACTORY_PID:
                raise PreservationError("Bind the factory USB identity before selecting ROM mode")
            self.identity_hash = identity_hash
        elif identity_hash != self.identity_hash:
            raise PreservationError("USB unique identity changed across enumeration; device access refused")
        actual_bus, address = int(read("busnum")), int(read("devnum"))
        if bus is not None and actual_bus != bus:
            raise PreservationError("Selected physical USB bus changed")
        node = self.dev_root / "bus/usb" / f"{actual_bus:03d}" / f"{address:03d}"
        if not stat.S_ISCHR(node.stat().st_mode):
            raise PreservationError("Selected USB node is not a character device")
        return USBTarget(self.topology, actual_bus, address, pid, str(node), identity_hash)

    def confirm(self, target):
        if self.target(target.pid, target.bus) != target:
            raise PreservationError("USB enumeration changed immediately before operation")

    def confirm_serial(self, target):
        self.confirm(target)
        port = self.port.resolve(strict=True)
        if not stat.S_ISCHR(port.stat().st_mode):
            raise PreservationError("Serial target is not a character device")
        device = (self.sys_root / "class/tty" / port.name / "device").resolve(strict=True)
        if self.usb_path.resolve(strict=True) not in device.parents:
            raise PreservationError("Serial port does not belong to selected USB topology")
        return str(port)

    def wait(self, pid, bus, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                return self.target(pid, bus)
            except (OSError, PreservationError):
                time.sleep(0.1)
        raise PreservationError("Expected USB mode did not enumerate on selected topology")


def identity_frame(command, sequence):
    if command not in (1, 6):
        raise PreservationError("Only HELLO and STATUS are allowed on the factory serial port")
    return HEADER.pack(b"FLDR", 1, command, 0, sequence, 0, 0)


def parse_response(data, sequence):
    if len(data) < HEADER.size:
        return None
    magic, version, kind, flags, actual_sequence, length, crc = HEADER.unpack_from(data)
    if magic != b"FLDR" or version != 1 or flags != 0 or actual_sequence != sequence:
        raise PreservationError("Factory response framing/sequence mismatch")
    if kind != 0x80 or not 12 <= length <= 4096:
        raise PreservationError("Factory did not return a bounded ACK")
    if len(data) < HEADER.size + length:
        return None
    payload = bytes(data[HEADER.size:HEADER.size + length])
    if zlib.crc32(payload) & 0xffffffff != crc:
        raise PreservationError("Factory response CRC failed")
    code, detail, written = struct.unpack_from("<III", payload)
    if code != 0 or detail != 0 or written != 0:
        raise PreservationError("Factory loader is not idle; preservation reset refused")
    return {"sequence": sequence, "response_type": kind, "code": code,
            "detail": detail, "bytes_written": written, "response_crc_valid": True}


def query_factory(inspector, target, store, label, serial_factory=None):
    if serial_factory is None:
        import serial
        serial_factory = serial.Serial
    inspector.confirm_serial(target)
    results = []
    with serial_factory(port=None, baudrate=115200, timeout=0.2,
                        write_timeout=1, exclusive=True) as port:
        port.dtr = False
        port.rts = False
        port.port = str(inspector.port)
        port.open()
        inspector.confirm_serial(target)
        port.reset_input_buffer()
        for sequence, command in ((1, 1), (2, 6)):
            inspector.confirm_serial(target)
            frame = identity_frame(command, sequence)
            if port.write(frame) != len(frame):
                raise PreservationError("Incomplete factory identity request")
            port.flush()
            data = bytearray()
            deadline = time.monotonic() + 4
            response = None
            try:
                while time.monotonic() < deadline:
                    data.extend(port.read(256))
                    # Retain only a bounded transcript; no unbounded memory on malformed input.
                    if len(data) > 8192:
                        raise PreservationError("Unbounded factory response")
                    if data:
                        response = parse_response(data, sequence)
                    if response is not None:
                        break
                if response is None:
                    raise PreservationError("Factory response timeout")
                response["command"] = "HELLO" if command == 1 else "STATUS"
                results.append(response)
            finally:
                store.create(f"{label}-{sequence}-response.bin", bytes(data))
    return {"responses": results, "serial_closed": True}


def picotool_args(operation, target, backup=None):
    required_pid = FACTORY_PID if operation == "boot" else BOOT_PID
    if target.pid != required_pid:
        raise PreservationError("Picotool operation selected the wrong USB mode")
    if operation == "boot":
        args = ["reboot", "-u", "-f"]
    elif operation == "return":
        args = ["reboot", "-a"]
    elif operation == "info":
        args = ["info", "-a"]
    elif operation in ("save", "verify"):
        if backup is None or Path(backup).name not in ("original-a.bin", "original-b.bin"):
            raise PreservationError("Only dedicated private backup files may be selected")
        args = (["save", "-a", "-v"] if operation == "save" else ["verify"]) + [str(backup), "-t", "bin"]
    else:
        raise PreservationError("Picotool operation is not permitted")
    return args + ["--bus", str(target.bus), "--address", str(target.address)]


def docker_command(tool, image, target, private_dir, args, name, uid):
    tool = str(Path(tool).resolve())
    if not tool.startswith("/nix/store/"):
        raise PreservationError("Container route requires the Nix picotool executable")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise PreservationError("Container image must be a loaded immutable sha256 image ID")
    if "," in str(private_dir):
        raise PreservationError("Docker bind path must not contain a comma")
    return ["docker", "run", "--rm", "--pull=never", "--name", name,
            "--network", "none", "--read-only", "--user", f"{uid}:0",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--device", target.node,
            "--mount", "type=bind,src=/nix/store,dst=/nix/store,readonly",
            "--mount", f"type=bind,src={private_dir},dst=/private",
            "--entrypoint", tool, image] + args


class Picotool:
    def __init__(self, tool, inspector, store, image=None):
        self.tool, self.inspector, self.store, self.image = tool, inspector, store, image
        self.steps = []
        self.hardware_process_closed = True

    def run(self, operation, target, backup=None):
        if not self.hardware_process_closed:
            raise PreservationError("Owned USB container closure is unverified; further device access refused")
        if backup is not None:
            backup = Path(backup)
            if backup.parent.resolve() != self.store.path or backup.is_symlink():
                raise PreservationError("Backup command escaped the owned private directory")
            info = backup.stat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise PreservationError("Backup command requires a precreated private regular file")
        path = Path("/private") / backup.name if backup is not None and self.image else backup
        args = picotool_args(operation, target, path)
        name = "esp-sdr-forgix-" + uuid.uuid4().hex
        command = (docker_command(self.tool, self.image, target, self.store.path, args, name, os.getuid())
                   if self.image else [self.tool] + args)
        self.inspector.confirm(target)  # Last check immediately before each process starts.
        record = {"operation": operation, "started_at_utc": utc(), "command": command}
        interrupted = False
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except BaseException as error:
            interrupted = True
            if self.image:
                self.hardware_process_closed = False
            record.update(exit_code=None, error_type=type(error).__name__,
                          stdout=str(getattr(error, "stdout", "") or ""),
                          stderr=str(getattr(error, "stderr", "") or ""))
            raise
        finally:
            if interrupted and self.image:
                # Only our uniquely named container; no global stop or USB permission changes.
                try:
                    cleanup = subprocess.run(["docker", "rm", "--force", name],
                                             capture_output=True, text=True, timeout=20)
                    record["container_cleanup_exit_code"] = cleanup.returncode
                    self.hardware_process_closed = cleanup.returncode == 0
                except BaseException as cleanup_error:
                    record["container_cleanup_failure_type"] = type(cleanup_error).__name__
            record["finished_at_utc"] = utc()
            record["hardware_process_closed"] = self.hardware_process_closed
            raw = (json.dumps(record, indent=2) + "\n").encode()
            self.store.create(f"step-{len(self.steps) + 1:02d}.json", raw)
            self.steps.append({key: record[key] for key in
                               ("operation", "started_at_utc", "finished_at_utc", "exit_code")})
            self.steps[-1]["private_transcript_sha256"] = sha256(raw)
            self.steps[-1]["hardware_process_closed"] = self.hardware_process_closed
        if result.returncode != 0:
            raise PreservationError("Picotool operation failed; see private transcript")
        return result.stdout


def flash_capacity(info):
    matches = re.findall(r"(?im)^\s*flash size:\s*(\d+)\s*([KMG]?)\s*(?:B)?\s*$", info)
    if len(matches) != 1:
        raise PreservationError("Picotool did not report an unambiguous flash size")
    amount, unit = matches[0]
    size = int(amount) * {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[unit.upper()]
    if size <= 0:
        raise PreservationError("Invalid detected flash size")
    return size


def check_backups(paths, expected_bytes):
    hashes = []
    for path in paths:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise PreservationError("Backup is not a private regular file")
        if info.st_size != expected_bytes:
            raise PreservationError("Backup is not the full expected flash length")
        hashes.append(sha256(path.read_bytes()))
    if len(hashes) != 2 or hashes[0] != hashes[1]:
        raise PreservationError("Independent full-flash reads differ")
    return {"bytes_per_read": expected_bytes, "reads": 2, "sha256": hashes[0], "matching": True}


def preserve(inspector, runner, store, expected_bytes, query=query_factory):
    receipt = {"schema_version": 1, "started_at_utc": utc(), "status": "unverified",
               "firmware_written": False, "fpga_programming_requested": False,
               "tool_provenance": getattr(runner, "provenance", None),
               "scope": "Detected RP flash range only; excludes OTP, RAM and FPGA configuration",
               "capacity_method": "Picotool detected flash size; not an independent JEDEC/BOM measurement"}
    factory = inspector.target(FACTORY_PID)
    store.json("usb-identity-private.json", {"topology": factory.topology, "bus": factory.bus,
               "initial_address": factory.address, "initial_serial_sha256": factory.serial_sha256})
    receipt["initial_application"] = query(inspector, factory, store, "initial")
    boot_requested = False
    primary_error = None
    try:
        boot_requested = True  # Even a lost ACK/timeout may have caused the requested reset.
        runner.run("boot", factory)
        boot = inspector.wait(BOOT_PID, factory.bus)
        size = flash_capacity(runner.run("info", boot))
        if size != expected_bytes:
            raise PreservationError("Detected flash capacity differs from explicit expected capacity")
        paths = [store.create(name) for name in ("original-a.bin", "original-b.bin")]
        for path in paths:
            runner.run("save", inspector.target(BOOT_PID, factory.bus), path)
        receipt["backups"] = check_backups(paths, size)
        runner.run("verify", inspector.target(BOOT_PID, factory.bus), paths[0])
        receipt["independent_device_verify"] = True
    except BaseException as error:
        primary_error = error
        receipt["failure_type"] = type(error).__name__
        store.json("failure-private.json", {"type": type(error).__name__, "message": str(error)})
    finally:
        if boot_requested:
            try:
                if not runner.hardware_process_closed:
                    raise PreservationError("Recovery waits for confirmed closure of the owned USB process")
                # A failed boot request can leave the original factory application running.
                try:
                    returned = inspector.target(FACTORY_PID, factory.bus)
                except (OSError, PreservationError):
                    boot = inspector.wait(BOOT_PID, factory.bus)
                    runner.run("return", boot)
                    returned = inspector.wait(FACTORY_PID, factory.bus)
                receipt["returned_application"] = query(inspector, returned, store, "returned")
            except BaseException as error:
                receipt["return_failure_type"] = type(error).__name__
                store.json("return-failure-private.json", {"type": type(error).__name__, "message": str(error)})
                if primary_error is None:
                    primary_error = error
        receipt.update(finished_at_utc=utc(), steps=runner.steps)
        receipt["status"] = "preserved_and_returned" if primary_error is None else "failed"
        store.json("receipt.json", receipt)
    return receipt, primary_error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usb-topology", required=True, help="Explicit physical sysfs USB path, e.g. 3-3")
    parser.add_argument("--serial-port", required=True, help="Explicit factory port, preferably stable /dev/serial/by-id path")
    parser.add_argument("--private-dir", required=True, type=Path, help="Fresh directory below ignored backups/")
    parser.add_argument("--expected-flash-bytes", type=int, default=2097152, help="Expected full RP2354 flash size (default 2097152)")
    parser.add_argument("--public-receipt", type=Path, help="Optional fresh sanitized JSON file below docs/evidence/")
    parser.add_argument("--usb-container", action="store_true", help="Use the Nix-built USB container for host permission limitations")
    parser.add_argument("--container-image", default=os.environ.get("PICOTOOL_CONTAINER_IMAGE_ID"), help="Loaded immutable sha256 image ID, never a tag or archive path")
    args = parser.parse_args(argv)
    parser.error('Legacy physical preservation entrypoint is retired. Use the exclusive, identity-bound forgix:usb-ram:recover task with the original private session and backups; preserve() remains available to its guarded backend.')


if __name__ == "__main__":
    raise SystemExit(main())
