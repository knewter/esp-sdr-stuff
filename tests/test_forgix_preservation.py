"""Forgix preservation safety/failure recovery tests; no hardware interfaces."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import preserve_forgix as p


FACTORY = p.USBTarget("3-3", 3, 26, p.FACTORY_PID, "/dev/bus/usb/003/026")
BOOT = p.USBTarget("3-3", 3, 27, p.BOOT_PID, "/dev/bus/usb/003/027")
RETURNED = p.USBTarget("3-3", 3, 28, p.FACTORY_PID, "/dev/bus/usb/003/028")


def ack(sequence=1, code=0, state=0, written=0, kind=0x80):
    # Independent protocol fixture, including a message that must remain private.
    payload = struct.pack("<III", code, state, written) + b"device unique PRIVATE"
    return struct.pack("<4sBBHIII", b"FLDR", 1, kind, 0, sequence,
                       len(payload), zlib.crc32(payload)) + payload


class FakeInspector:
    def __init__(self):
        self.current = FACTORY
        self.port = Path("/dev/fake-explicit-port")
        self.confirmations = []

    def target(self, pid, bus=None):
        if self.current.pid != pid or (bus is not None and self.current.bus != bus):
            raise p.PreservationError("Wrong mode")
        return self.current

    def confirm(self, target):
        self.confirmations.append(target)
        if self.current != target:
            raise p.PreservationError("Stale USB target")

    def confirm_serial(self, target):
        self.confirm(target)

    def wait(self, pid, bus, seconds=30):
        return self.target(pid, bus)


class FakeRunner:
    def __init__(self, inspector, fail=None, info="flash size: 8B", different=False):
        self.inspector = inspector
        self.fail = fail
        self.info = info
        self.different = different
        self.steps = []
        self.hardware_process_closed = True

    def run(self, operation, target, backup=None):
        self.inspector.confirm(target)
        self.steps.append({"operation": operation})
        if operation == "boot":
            self.inspector.current = BOOT
        if self.fail == operation:
            raise p.PreservationError("Injected failure")
        if operation == "info":
            return self.info
        if operation == "save":
            data = b"ABCDEFGH"
            if self.different and backup.name == "original-b.bin":
                data = b"abcdEFGH"
            backup.write_bytes(data)
        if operation == "return":
            self.inspector.current = RETURNED
        return "OK"


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = p.PrivateStore(self.root / "new", self.root)

    def tearDown(self):
        self.temp.cleanup()

    def query(self, inspector, target, store, label):
        inspector.confirm(target)
        return {"responses": [p.parse_response(ack(), 1)], "serial_closed": True}

    def trial(self, **kwargs):
        inspector = FakeInspector()
        runner = FakeRunner(inspector, **kwargs)
        receipt, error = p.preserve(inspector, runner, self.store, 8, query=self.query)
        return inspector, runner, receipt, error

    def test_full_read_comparison_independent_verify_and_factory_return(self):
        inspector, runner, receipt, error = self.trial()
        self.assertIsNone(error)
        self.assertEqual(receipt["status"], "preserved_and_returned")
        self.assertEqual([s["operation"] for s in runner.steps],
                         ["boot", "info", "save", "save", "verify", "return"])
        self.assertEqual(receipt["backups"]["bytes_per_read"], 8)
        self.assertEqual(receipt["backups"]["sha256"], p.sha256(b"ABCDEFGH"))
        self.assertTrue(receipt["independent_device_verify"])
        self.assertEqual(inspector.current, RETURNED)
        self.assertNotIn("PRIVATE", json.dumps(receipt))

    def test_failed_save_still_returns_factory_and_never_claims_preserved(self):
        _, runner, receipt, error = self.trial(fail="save")
        self.assertIsNotNone(error)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(runner.steps[-1]["operation"], "return")
        self.assertIn("returned_application", receipt)
        self.assertNotIn("independent_device_verify", receipt)

    def test_failed_verify_keeps_matching_backups_but_gate_fails(self):
        _, _, receipt, error = self.trial(fail="verify")
        self.assertIsNotNone(error)
        self.assertTrue(receipt["backups"]["matching"])
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("returned_application", receipt)

    def test_mismatched_full_reads_are_retained_and_not_verified(self):
        _, runner, receipt, error = self.trial(different=True)
        self.assertIsNotNone(error)
        self.assertEqual(len(list(self.store.path.glob("original-*.bin"))), 2)
        self.assertNotIn("verify", [s["operation"] for s in runner.steps])
        self.assertEqual(runner.steps[-1]["operation"], "return")

    def test_capacity_mismatch_performs_no_reads_and_returns_application(self):
        _, runner, receipt, error = self.trial(info="flash size: 16B")
        self.assertIsNotNone(error)
        self.assertNotIn("save", [s["operation"] for s in runner.steps])
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(runner.steps[-1]["operation"], "return")

    def test_return_failure_cannot_be_reported_as_success(self):
        _, _, receipt, error = self.trial(fail="return")
        self.assertIsNotNone(error)
        self.assertTrue(receipt["independent_device_verify"])
        self.assertNotIn("returned_application", receipt)
        self.assertEqual(receipt["status"], "failed")

    def test_lost_boot_ack_still_attempts_application_return(self):
        inspector, runner, receipt, error = self.trial(fail="boot")
        self.assertIsNotNone(error)
        self.assertEqual([s["operation"] for s in runner.steps], ["boot", "return"])
        self.assertEqual(inspector.current, RETURNED)
        self.assertEqual(receipt["status"], "failed")

    def test_initial_factory_failure_requests_no_reset(self):
        inspector = FakeInspector()
        runner = FakeRunner(inspector)
        with self.assertRaises(p.PreservationError):
            p.preserve(inspector, runner, self.store, 8,
                       query=lambda *args: (_ for _ in ()).throw(p.PreservationError("CRC")))
        self.assertEqual(runner.steps, [])

    def test_private_files_are_restricted_at_creation_and_cannot_overwrite(self):
        path = self.store.create("raw.bin", b"original")
        self.assertEqual(stat.S_IMODE(self.store.path.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            self.store.create("raw.bin", b"replacement")
        self.assertEqual(path.read_bytes(), b"original")
        with self.assertRaises(p.PreservationError):
            self.store.create("../escape.bin")
        with self.assertRaises(FileExistsError):
            p.PrivateStore(self.store.path, self.root)
        with self.assertRaises(p.PreservationError):
            p.PrivateStore(self.root.parent / "outside", self.root)

    def test_matching_short_or_public_files_cannot_pass_full_backup_gate(self):
        paths = [self.store.create(n, b"1234") for n in ("original-a.bin", "original-b.bin")]
        with self.assertRaises(p.PreservationError):
            p.check_backups(paths, 8)
        paths[0].chmod(0o644)
        with self.assertRaises(p.PreservationError):
            p.check_backups(paths, 4)

    def test_protocol_rejects_bad_crc_sequence_busy_error_and_nack(self):
        self.assertIsNone(p.parse_response(ack()[:10], 1))
        self.assertIsNone(p.parse_response(ack()[:22], 1))
        malformed = [ack(sequence=2), ack(code=1), ack(state=1), ack(written=1),
                     ack(kind=0x81), ack()[:-1] + b"X"]
        for frame in malformed:
            with self.subTest(frame=frame), self.assertRaises(p.PreservationError):
                p.parse_response(frame, 1)
        self.assertNotIn("PRIVATE", json.dumps(p.parse_response(ack(), 1)))
        with self.assertRaises(p.PreservationError):
            p.identity_frame(2, 1)

    def test_picotool_allowlist_and_bus_address_scoping(self):
        for operation in ("info", "save", "verify", "return"):
            args = p.picotool_args(operation, BOOT, self.store.path / "original-a.bin")
            self.assertEqual(args[-4:], ["--bus", "3", "--address", "27"])
            self.assertNotIn("-f", args)
            self.assertNotIn("-F", args)
        self.assertEqual(p.picotool_args("boot", FACTORY)[:3], ["reboot", "-u", "-f"])
        for operation in ("erase", "load", "otp", "save", "boot"):
            with self.subTest(operation=operation), self.assertRaises(p.PreservationError):
                p.picotool_args(operation, BOOT if operation != "save" else FACTORY)
        with self.assertRaises(p.PreservationError):
            p.picotool_args("save", BOOT, Path("/arbitrary.bin"))

    def test_usb_reenumeration_blocks_process_launch(self):
        inspector = FakeInspector()
        runner = p.Picotool("/nix/store/tool/bin/picotool", inspector, self.store)
        inspector.current = RETURNED
        with patch.object(p.subprocess, "run") as command:
            with self.assertRaises(p.PreservationError):
                runner.run("boot", FACTORY)
            command.assert_not_called()

    def test_container_has_one_device_two_mounts_no_network_or_capabilities(self):
        args = p.docker_command("/nix/store/tool/bin/picotool", "sha256:" + "a"*64,
                                BOOT, self.store.path, ["info"], "owned", 1000)
        self.assertEqual(args.count("--device"), 1)
        self.assertEqual(args[args.index("--device") + 1], BOOT.node)
        self.assertEqual(args.count("--mount"), 2)
        self.assertIn("type=bind,src=/nix/store,dst=/nix/store,readonly", args)
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertEqual(args[args.index("--cap-drop") + 1], "ALL")
        self.assertIn("--pull=never", args)
        self.assertIn("--read-only", args)
        self.assertNotIn("--privileged", args)
        for tool, image in [("/usr/bin/picotool", "sha256:" + "a"*64),
                            ("/nix/store/tool/picotool", "mutable:tag")]:
            with self.assertRaises(p.PreservationError):
                p.docker_command(tool, image, BOOT, self.store.path, [], "owned", 1000)

    def test_container_timeout_removes_only_owned_container_and_logs_failure(self):
        inspector = FakeInspector()
        inspector.current = BOOT
        runner = p.Picotool("/nix/store/tool/bin/picotool", inspector, self.store,
                            "sha256:" + "a"*64)
        def execute(command, **kwargs):
            if command[1] == "run":
                raise subprocess.TimeoutExpired(command, 180, output=b"private UNIQUE")
            return subprocess.CompletedProcess(command, 0, "removed", "")
        with patch.object(p.subprocess, "run", side_effect=execute) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.run("info", BOOT)
        launch, cleanup = [c.args[0] for c in run.call_args_list]
        self.assertEqual(cleanup, ["docker", "rm", "--force", launch[launch.index("--name") + 1]])
        self.assertTrue(runner.hardware_process_closed)
        self.assertIsNone(runner.steps[0]["exit_code"])
        self.assertNotIn("UNIQUE", json.dumps(runner.steps))
        self.assertIn("UNIQUE", (self.store.path / "step-01.json").read_text())

    def test_unverified_container_closure_refuses_another_usb_operation(self):
        inspector = FakeInspector()
        inspector.current = BOOT
        runner = p.Picotool("/nix/store/tool/bin/picotool", inspector, self.store,
                            "sha256:" + "a"*64)
        with patch.object(p.subprocess, "run", side_effect=[
                subprocess.TimeoutExpired("owned", 180),
                subprocess.CompletedProcess("remove", 1, "", "failure")]):
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.run("info", BOOT)
        self.assertFalse(runner.hardware_process_closed)
        with patch.object(p.subprocess, "run") as run:
            with self.assertRaises(p.PreservationError):
                runner.run("return", BOOT)
            run.assert_not_called()

    def test_recovery_does_not_compete_with_an_unclosed_owned_usb_process(self):
        inspector = FakeInspector()
        class UnclosedRunner(FakeRunner):
            def run(self, operation, target, backup=None):
                if operation == "info":
                    self.hardware_process_closed = False
                    self.steps.append({"operation": "info"})
                    raise p.PreservationError("Container closure unverified")
                return super().run(operation, target, backup)
        runner = UnclosedRunner(inspector)
        receipt, error = p.preserve(inspector, runner, self.store, 8, query=self.query)
        self.assertIsNotNone(error)
        self.assertEqual([step["operation"] for step in runner.steps], ["boot", "info"])
        self.assertEqual(inspector.current, BOOT)
        self.assertNotIn("returned_application", receipt)
        self.assertIn("return_failure_type", receipt)

    def test_picotool_rejects_backup_outside_private_directory_before_process_launch(self):
        inspector = FakeInspector()
        inspector.current = BOOT
        runner = p.Picotool("/nix/store/tool/bin/picotool", inspector, self.store)
        foreign = self.root / "original-a.bin"
        foreign.write_bytes(b"original")
        foreign.chmod(0o600)
        with patch.object(p.subprocess, "run") as command:
            with self.assertRaises(p.PreservationError):
                runner.run("save", BOOT, foreign)
            command.assert_not_called()
        self.assertEqual(foreign.read_bytes(), b"original")

    def test_flash_capacity_is_unambiguous_and_accepts_native_picotool_format(self):
        self.assertEqual(p.flash_capacity(" flash size:             2048K\n"), 2097152)
        for info in ("", "flash size: 0K", "flash size: 1K\nflash size: 2K", "flash size: unknown"):
            with self.assertRaises(p.PreservationError):
                p.flash_capacity(info)

    def test_help_and_missing_targets_touch_no_hardware(self):
        with patch.object(p.shutil, "which") as lookup, patch.object(p, "Inspector") as inspector:
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                p.main(["--help"])
            self.assertEqual(result.exception.code, 0)
            lookup.assert_not_called()
            inspector.assert_not_called()
        with patch.object(p, "Inspector") as inspector, patch.object(p.subprocess, "run") as run:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                p.main([])
            inspector.assert_not_called()
            run.assert_not_called()

    def test_serial_port_must_belong_to_the_explicit_usb_topology(self):
        sysroot = self.root / "sys"
        devroot = self.root / "dev"
        usb = sysroot / "bus/usb/devices/3-3"
        usb.mkdir(parents=True)
        for name, value in {"idVendor": "2e8a", "idProduct": "0009", "busnum": "3", "devnum": "26", "serial": "E660123456789ABC"}.items():
            (usb / name).write_text(value)
        node = devroot / "bus/usb/003/026"
        node.parent.mkdir(parents=True)
        node.symlink_to("/dev/null")
        serial = devroot / "ttyACM2"
        serial.symlink_to("/dev/null")
        # /dev/null is a character node; its sysfs ancestry is deliberately foreign.
        tty = sysroot / "class/tty/null"
        tty.mkdir(parents=True)
        foreign = sysroot / "foreign"
        foreign.mkdir()
        (tty / "device").symlink_to(foreign)
        inspector = p.Inspector("3-3", serial, sysroot, devroot)
        target = inspector.target(p.FACTORY_PID)
        with self.assertRaises(p.PreservationError):
            inspector.confirm_serial(target)
        (usb / "idVendor").write_text("10c4")
        with self.assertRaises(p.PreservationError):
            inspector.target(p.FACTORY_PID)
        for topology in ("*", "../3-3", "3-3:1.0", "usb3"):
            with self.assertRaises(p.PreservationError):
                p.Inspector(topology, serial, sysroot, devroot)

    def test_same_topology_with_different_unique_id_cannot_replace_selected_board(self):
        sysroot = self.root / "sys"
        devroot = self.root / "dev"
        usb = sysroot / "bus/usb/devices/3-3"
        usb.mkdir(parents=True)
        for name, value in {"idVendor": "2e8a", "idProduct": "0009", "busnum": "3", "devnum": "26", "serial": "E660123456789ABC"}.items():
            (usb / name).write_text(value)
        node = devroot / "bus/usb/003/026"
        node.parent.mkdir(parents=True)
        node.symlink_to("/dev/null")
        inspector = p.Inspector("3-3", devroot / "ttyACM2", sysroot, devroot)
        target = inspector.target(p.FACTORY_PID)
        self.assertEqual(target.serial_sha256, p.sha256(b"e660123456789abc"))
        (usb / "idProduct").write_text("000f")
        (usb / "serial").write_text("e660123456789abc\n")
        self.assertEqual(inspector.target(p.BOOT_PID).serial_sha256, target.serial_sha256)
        (usb / "serial").write_text("OTHER-BOARD")
        with self.assertRaises(p.PreservationError):
            inspector.target(p.BOOT_PID)

    def test_serial_query_closes_on_bad_response_and_never_sends_configuration(self):
        inspector = FakeInspector()
        class Serial:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.frames = []
                self.closed = False
                self.opened = False
            def __enter__(self): return self
            def __exit__(self, *args): self.closed = True
            def open(self):
                self.opened = True
                self.controls_at_open = (self.dtr, self.rts)
            def reset_input_buffer(self): pass
            def write(self, frame):
                self.frames.append(frame)
                return len(frame)
            def flush(self): pass
            def read(self, size): return ack(state=1)
        serial = Serial()
        with self.assertRaises(p.PreservationError):
            p.query_factory(inspector, FACTORY, self.store, "initial", serial_factory=lambda **kwargs: serial)
        self.assertTrue(serial.closed)
        self.assertEqual(serial.controls_at_open, (False, False))
        self.assertEqual(serial.frames, [p.identity_frame(1, 1)])
        self.assertEqual((self.store.path / "initial-1-response.bin").read_bytes(), ack(state=1))


if __name__ == "__main__":
    unittest.main()
