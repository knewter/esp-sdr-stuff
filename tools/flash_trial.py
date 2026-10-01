#!/usr/bin/env python3
"""Install the pinned SDR trial or restore the verified private baseline."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from esp_sdr_capture import STABLE_PORT, SOURCE_REVISION

ROOT = Path(__file__).resolve().parents[1]
SDK_REVISION = "25fe69f946311abdaf9ad56591f25fedbc20ac98"
DIAGNOSTIC_PATCH_SHA256 = "fb2d465c97f8385b199b51cc8878ed5988790584f22c758c62a0a26dfee7698c"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "restore"))
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/evidence/firmware-artifact/manifest.json")
    parser.add_argument("--port", default=STABLE_PORT, choices=(STABLE_PORT,))
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    backup = ROOT / "backups/original.bin"
    manifest = json.loads((ROOT / "docs/evidence/firmware-preservation/manifest.json").read_text())
    if backup.stat().st_size != 0x400000 or sha(backup) != manifest["sha256"] or not manifest["read_hashes_equal"]:
        raise SystemExit("Preservation image does not match verified manifest")
    security = (ROOT / "docs/evidence/firmware-preservation/security.log").read_text()
    for field in ("ABS_DONE_0", "ABS_DONE_1"):
        if not re.search(rf"^{field}\s+.*= False\s", security, flags=re.M):
            raise SystemExit("Secure boot state is not verified disabled")
    if not re.search(r"^FLASH_CRYPT_CNT\s+.*= 0\s", security, flags=re.M):
        raise SystemExit("Flash encryption state is not verified disabled")
    if subprocess.run(["fuser", args.port], capture_output=True).returncode == 0:
        raise SystemExit("Serial device is already open")
    args.evidence.mkdir(parents=True, exist_ok=False)
    command = ["esptool", "--chip", "esp32", "--port", args.port, "--baud", "460800", "write-flash", "--no-progress"]
    parts = []
    if args.action == "install":
        if args.artifact is None:
            parser.error("install requires --artifact")
        artifact = json.loads(args.manifest.read_text())
        profile = artifact["variants"]["esp32"]
        if artifact["version"] == SOURCE_REVISION:
            canonical = json.loads((ROOT / "docs/evidence/firmware-artifact/manifest.json").read_text())
            if artifact != canonical:
                raise SystemExit("Upstream artifact manifest differs from the verified acquisition")
        else:
            build = json.loads(args.manifest.with_name("build-info.json").read_text())
            if build.get("kind") == "diagnostic build; not an RF baseline":
                patch = args.manifest.with_name("diagnostic.patch")
                verified = (build.get("source_base_commit") == SOURCE_REVISION and
                            build.get("idf_commit") == SDK_REVISION and
                            build.get("target") == "esp32" and
                            build.get("app_version") == artifact["version"] == "550fade-diag115k" and
                            build.get("baud_default") == 115200 and
                            build.get("source_patch") == patch.name and
                            build.get("source_patch_sha256") == DIAGNOSTIC_PATCH_SHA256 and
                            sha(patch) == DIAGNOSTIC_PATCH_SHA256)
            else:
                difference = build.get("configuration_difference_from_upstream_defaults", {})
                verified = (build.get("source_commit") == SOURCE_REVISION and
                            build.get("idf_commit") == SDK_REVISION and
                            build.get("target") == "esp32" and
                            build.get("app_version") == artifact["version"] and
                            set(difference) == {"CONFIG_ESP_SDR_UART_BAUD"} and
                            difference["CONFIG_ESP_SDR_UART_BAUD"] in (115200, 460800, 921600, 1000000) and
                            build.get("source_code_patch", "missing") is None)
            if not verified:
                raise SystemExit("Local build provenance is not a verified transport or diagnostic variant")
        if profile["target"] != "esp32":
            raise SystemExit("Unexpected source revision or silicon target")
        if [part["offset"] for part in profile["parts"]] != [0x1000, 0x8000, 0x10000]:
            raise SystemExit("Unexpected target flash offsets")
        if [part["name"] for part in profile["parts"]] != ["0-bootloader.bin", "1-partition-table.bin", "2-esp_sdr.bin"]:
            raise SystemExit("Unexpected artifact part names")
        for part, end in zip(profile["parts"], (0x8000, 0x9000, 0x110000)):
            if part["size"] <= 0 or part["offset"] + part["size"] > end:
                raise SystemExit("Artifact overlaps another partition or exceeds the factory application")
        command += ["--flash-mode", "dio", "--flash-freq", "40m", "--flash-size", "2MB"]
        for part in profile["parts"]:
            path = args.artifact / "esp32" / part["name"]
            if path.stat().st_size != part["size"] or sha(path) != part["sha256"]:
                raise SystemExit("Artifact length/hash mismatch")
            if part["offset"] + part["size"] > 0x400000:
                raise SystemExit("Artifact exceeds flash")
            command += [hex(part["offset"]), str(path)]
            parts.append({"offset": part["offset"], "bytes": part["size"], "sha256": part["sha256"], "name": part["name"]})
    else:
        command += ["0", str(backup)]
        parts.append({"offset": 0, "bytes": manifest["bytes"], "sha256": manifest["sha256"], "name": "private original image"})
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, text=True, capture_output=True, timeout=600)
    log = re.sub(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", "[redacted device address]", result.stdout + result.stderr)
    log = log.replace(str(args.artifact), "ARTIFACT_DIRECTORY") if args.artifact else log
    log = log.replace(str(backup), "backups/original.bin")
    (args.evidence / "write.log").write_text(log)
    record = {"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "action": args.action, "exit_code": result.returncode, "parts": parts,
              "baseline_sha256_checked": manifest["sha256"], "source_revision": SOURCE_REVISION if args.action == "install" else "preserved baseline",
              "force_used": False, "efuses_written": False,
              "boot_proven": False, "power_cycle_proven": False}
    if args.action == "install":
        record["firmware_variant"] = artifact["version"]
    (args.evidence / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    if result.returncode:
        raise SystemExit(f"Flash operation failed; inspect {args.evidence}/write.log")
    print(f"{args.action} write and esptool hash verification passed; boot proof still required")

if __name__ == "__main__":
    main()
