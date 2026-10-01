"""Independent flash-guard regressions. Every external command is mocked."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "tools"))
import flash_trial as trial


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class FlashGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.backup = self.root / "backups/original.bin"
        self.backup.parent.mkdir()
        self.backup.write_bytes(b"\xff" * 0x400000)
        self.baseline = {"sha256": hashlib.sha256(self.backup.read_bytes()).hexdigest(),
                         "bytes": 0x400000, "read_hashes_equal": True}
        self.preservation = self.root / "docs/evidence/firmware-preservation"
        write_json(self.preservation / "manifest.json", self.baseline)
        self.security = ("ABS_DONE_0 (BLOCK0) secure boot V1 = False R/W\n"
                         "ABS_DONE_1 (BLOCK0) secure boot V2 = False R/W\n"
                         "FLASH_CRYPT_CNT (BLOCK0) encrypted flash = 0 R/W\n")
        (self.preservation / "security.log").write_text(self.security)
        self.artifact = self.root / "private-artifact"
        (self.artifact / "esp32").mkdir(parents=True)
        self.canonical = copy.deepcopy(json.loads((REPOSITORY / "docs/evidence/firmware-artifact/manifest.json").read_text()))
        for index, part in enumerate(self.canonical["variants"]["esp32"]["parts"]):
            data = bytes([index + 1]) * 64
            (self.artifact / "esp32" / part["name"]).write_bytes(data)
            part["size"] = len(data)
            part["sha256"] = hashlib.sha256(data).hexdigest()
        self.canonical_path = self.root / "docs/evidence/firmware-artifact/manifest.json"
        write_json(self.canonical_path, self.canonical)
        self.manifest_path = self.root / "candidate/manifest.json"
        self.candidate = copy.deepcopy(self.canonical)
        self.build = None
        self.commands = []
        self.occupied = False
        self.flash_exit = 0

    def configure(self, baud=921600):
        self.candidate["version"] = f"550fade-uart{baud}"
        self.candidate["variants"]["esp32"]["version"] = self.candidate["version"]
        self.build = {"source_commit": trial.SOURCE_REVISION, "idf_commit": trial.SDK_REVISION,
                      "target": "esp32", "app_version": self.candidate["version"],
                      "configuration_difference_from_upstream_defaults": {"CONFIG_ESP_SDR_UART_BAUD": baud},
                      "source_code_patch": None}

    def diagnostic(self):
        self.candidate["version"] = "550fade-diag115k"
        self.candidate["variants"]["esp32"]["version"] = self.candidate["version"]
        self.build = json.loads((REPOSITORY / "docs/evidence/firmware-diagnostic/build-info.json").read_text())
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = (REPOSITORY / "docs/evidence/firmware-diagnostic/diagnostic.patch").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), trial.DIAGNOSTIC_PATCH_SHA256)
        (self.manifest_path.parent / "diagnostic.patch").write_bytes(data)

    def command(self, command, **kwargs):
        self.commands.append(command)
        if command[0] == "fuser":
            return subprocess.CompletedProcess(command, int(not self.occupied), stdout=b"", stderr=b"")
        self.assertEqual(command[0], "esptool", "No other external tool may run")
        self.assertIn("write-flash", command)
        text = f"MAC: 12:34:56:78:9a:bc\n{self.artifact}\n{self.backup}\n"
        return subprocess.CompletedProcess(command, self.flash_exit, stdout=text, stderr="")

    def invoke(self, action="install", port=None):
        write_json(self.manifest_path, self.candidate)
        if self.build is not None:
            write_json(self.manifest_path.with_name("build-info.json"), self.build)
        self.output = self.root / "evidence-output"
        args = ["flash_trial.py", action, "--manifest", str(self.manifest_path), "--evidence", str(self.output)]
        if action == "install":
            args += ["--artifact", str(self.artifact)]
        if port is not None:
            args += ["--port", port]
        with patch.object(trial, "ROOT", self.root), patch.object(sys, "argv", args), \
             patch.object(trial.subprocess, "run", side_effect=self.command), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            trial.main()

    def rejected(self, message=None):
        with self.assertRaises(SystemExit) as caught:
            self.invoke()
        if message:
            self.assertIn(message, str(caught.exception))
        self.assertFalse(any(c[0] == "esptool" for c in self.commands), "Rejected input must not flash")

    def test_original_canonical_artifact_uses_exact_offsets_and_no_force(self):
        self.invoke()
        command = self.commands[-1]
        self.assertEqual(command[:5], ["esptool", "--chip", "esp32", "--port", trial.STABLE_PORT])
        self.assertEqual(command[-6::2], ["0x1000", "0x8000", "0x10000"])
        self.assertNotIn("--force", command)
        self.assertNotIn("--erase-all", command)
        record = json.loads((self.output / "manifest.json").read_text())
        self.assertFalse(record["boot_proven"])
        self.assertFalse(record["power_cycle_proven"])

    def test_same_source_label_cannot_bypass_acquisition_metadata(self):
        self.candidate["acquisition"]["build_info"]["idf_commit"] = "unreviewed-sdk"
        self.rejected("verified acquisition")

    def test_same_source_label_cannot_bypass_part_integrity(self):
        self.candidate["variants"]["esp32"]["parts"][2]["sha256"] = "0" * 64
        self.rejected("verified acquisition")

    def test_supported_config_only_bauds_are_allowed(self):
        for baud in [115200, 460800, 921600, 1000000]:
            with self.subTest(baud=baud):
                self.configure(baud)
                self.invoke()
                self.assertEqual(self.commands[-1][0], "esptool")
                shutil.rmtree(self.output)

    def test_unreviewed_sdk_source_target_or_version_cannot_flash(self):
        for key, value in [("idf_commit", "other-sdk"), ("source_commit", "other-source"),
                           ("target", "esp32s3"), ("app_version", "other-app")]:
            with self.subTest(key=key):
                self.configure()
                self.build[key] = value
                self.rejected("verified transport")
                if self.output.exists():
                        shutil.rmtree(self.output)

    def test_extra_config_or_source_changes_cannot_be_labeled_uart_only(self):
        self.configure()
        self.build["configuration_difference_from_upstream_defaults"]["CONFIG_FREERTOS_UNICORE"] = False
        self.rejected("verified transport")

    def test_config_only_variant_rejects_source_patch(self):
        self.configure()
        self.build["source_code_patch"] = "other.patch"
        self.rejected("verified transport")

    def test_unsupported_uart_baud_cannot_flash(self):
        self.configure(123456)
        self.rejected("verified transport")

    def test_exact_diagnostic_patch_and_pinned_provenance_are_allowed(self):
        self.diagnostic()
        self.invoke()
        self.assertEqual(self.commands[-1][0], "esptool")

    def test_modified_diagnostic_bytes_are_rejected_even_if_declared_hash_matches(self):
        self.diagnostic()
        with self.manifest_path.with_name("diagnostic.patch").open("ab") as stream:
            stream.write(b"\n/* unreviewed modification */\n")
        self.rejected("verified transport")

    def test_diagnostic_has_no_sdk_or_baud_exception(self):
        self.diagnostic()
        self.build["baud_default"] = 1000000
        self.rejected("verified transport")

    def test_noncanonical_offsets_and_path_traversal_names_are_rejected(self):
        for field, value in [("offset", 0), ("name", "../../unreviewed.bin")]:
            with self.subTest(field=field):
                self.configure()
                self.candidate["variants"]["esp32"]["parts"][0][field] = value
                self.rejected("Unexpected")
                if self.output.exists():
                        shutil.rmtree(self.output)
                self.candidate = copy.deepcopy(self.canonical)

    def test_parts_cannot_overlap_partition_boundaries(self):
        for index, size in [(0, 0x7001), (1, 0x1001), (2, 0x100001), (2, 0)]:
            with self.subTest(index=index, size=size):
                self.candidate = copy.deepcopy(self.canonical)
                self.configure()
                self.candidate["variants"]["esp32"]["parts"][index]["size"] = size
                self.rejected("overlaps")
                if self.output.exists():
                        shutil.rmtree(self.output)

    def test_changed_artifact_payload_cannot_flash(self):
        self.configure()
        (self.artifact / "esp32/2-esp_sdr.bin").write_bytes(b"x" * 64)
        self.rejected("length/hash")

    def test_changed_private_baseline_or_unverified_reads_block_install(self):
        self.backup.write_bytes(b"x" * 0x400000)
        self.rejected("Preservation")

    def test_incomplete_private_baseline_blocks_install(self):
        self.backup.write_bytes(b"short")
        self.rejected("Preservation")

    def test_independent_read_mismatch_blocks_install(self):
        self.baseline["read_hashes_equal"] = False
        write_json(self.preservation / "manifest.json", self.baseline)
        self.rejected("Preservation")

    def test_enabled_secure_boot_or_encryption_blocks_install(self):
        for text in [self.security.replace("= False", "= True", 1),
                     self.security.replace("= 0", "= 1")]:
            with self.subTest(text=text):
                (self.preservation / "security.log").write_text(text)
                self.rejected()

    def test_occupied_serial_port_blocks_install(self):
        self.occupied = True
        self.rejected("already open")

    def test_ambiguous_acm_port_is_rejected_before_any_external_command(self):
        with self.assertRaises(SystemExit):
            self.invoke(port="/dev/ttyACM0")
        self.assertFalse(self.commands)

    def test_restore_writes_whole_preserved_image_without_header_overrides(self):
        self.invoke(action="restore")
        command = self.commands[-1]
        self.assertEqual(command[-2:], ["0", str(self.backup)])
        for option in ["--force", "--flash-mode", "--flash-freq", "--flash-size", "--erase-all"]:
            self.assertNotIn(option, command)
        record = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(record["parts"][0]["bytes"], 0x400000)
        self.assertFalse(record["boot_proven"])
        self.assertFalse(record["power_cycle_proven"])

    def test_failed_flash_retains_failed_manifest_without_boot_claim(self):
        self.flash_exit = 2
        with self.assertRaises(SystemExit):
            self.invoke()
        record = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(record["exit_code"], 2)
        self.assertFalse(record["boot_proven"])

    def test_public_write_log_redacts_mac_and_private_paths(self):
        self.invoke()
        text = (self.output / "write.log").read_text()
        self.assertNotIn("12:34:56:78:9a:bc", text)
        self.assertNotIn(str(self.artifact), text)
        self.assertNotIn(str(self.backup), text)


if __name__ == "__main__":
    unittest.main()
