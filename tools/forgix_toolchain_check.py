#!/usr/bin/env python3
"""Check the pinned Forgix host environment without opening hardware.

Default checks imports, real RTL generation, and CLI help. Gateware compilation
requires an explicit device/clock/revision declaration and vendor installation.
No command in this tool programs hardware or replaces MCU firmware.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone


def command_check(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return {"command": Path(args[0]).name, "arguments": args[1:],
            "exit_code": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest()}


def parameters(device, clock_hz, revision, confirmed):
    if not confirmed or device not in ("T8F49C2", "T8F49I2") or not revision or not revision.strip() or not clock_hz:
        raise ValueError("Gateware requires confirmed FPGA device, oscillator frequency and board revision")
    if revision.strip().casefold() in ("unknown", "unverified", "tbd", "todo", "?"):
        raise ValueError("Board revision declaration is still a placeholder")
    if not 1_000_000 <= clock_hz <= 200_000_000:
        raise ValueError("Declared oscillator frequency is outside the supported planning range")
    return {"device": device, "clock_hz": clock_hz, "board_revision": revision,
            "confirmation": "User-supplied physical parameters; software has not measured them"}


def vendor_layout(root):
    if not root:
        return None
    path = Path(root).expanduser().resolve()
    if not (path / "bin/setup.sh").is_file() or not (path / "scripts/efx_run.py").is_file():
        raise ValueError("LITEX_ENV_EFINITY is not a complete Efinity installation")
    return path


def gateware_build(device_parameters, output, vendor):
    # Efinity itself is executed by the configured Nix FHS wrapper. No compile
    # until actual parameters are supplied; upstream defaults stay visible.
    if vendor is None:
        raise ValueError("Efinity installation/license required for gateware generation")
    if os.environ.get("FORGIX_INSIDE_EFINITY") != "1":
        raise ValueError("Run gateware compilation inside forgix-efinity with FORGIX_INSIDE_EFINITY=1")
    from litex.build.efinix.platform import EfinixPlatform
    from litex_boards.platforms import adiuvo_forgix as board
    from litex_boards.targets.adiuvo_forgix import BaseSoC
    from litex.soc.integration.builder import Builder
    clock = device_parameters["clock_hz"]
    class PhysicalPlatform(board.Platform):
        default_clk_freq = clock
        default_clk_period = 1e9 / clock

        def __init__(self):
            EfinixPlatform.__init__(self, device_parameters["device"], board._io, board._connectors,
                iobank_info=board._bank_info, toolchain="efinity", spi_mode="passive", spi_width="1")
    board.Platform = PhysicalPlatform
    try:
        soc = BaseSoC(sys_clk_freq=clock, with_spibone=True,
                      with_demo_leds=False, with_demo_io=False, with_demo_scope=False)
        builder = Builder(soc, output_dir=str(output), compile_software=False)
        builder.build()
    finally:
        # The process exits afterward, but avoid leaking the override to imports.
        board.Platform = PhysicalPlatform.__bases__[0]
    # Builder's default name varies by LiteX version; retain discovered files
    # instead of claiming a predetermined filename exists.
    images = sorted((output / "gateware/outflow").glob("*.hex"))
    if not images:
        raise ValueError("Compilation returned without a passive FPGA hex image")
    return [{"file": image.relative_to(output).as_posix(), "bytes": image.stat().st_size,
             "sha256": hashlib.sha256(image.read_bytes()).hexdigest()} for image in images]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional fresh JSON receipt; raw vendor output is not published")
    parser.add_argument("--require-vendor", action="store_true", help="Fail unless vendor installation and CLI help work")
    parser.add_argument("--plan", action="store_true", help="Validate explicit physical parameters without compiling")
    parser.add_argument("--build-dir", type=Path, help="Fresh gateware output directory; never programs a device")
    parser.add_argument("--device", choices=("T8F49C2", "T8F49I2"))
    parser.add_argument("--clock-hz", type=int)
    parser.add_argument("--board-revision")
    parser.add_argument("--verified-parameters", action="store_true")
    args = parser.parse_args(argv)
    if args.output and args.output.exists():
        parser.error("--output must be fresh")
    if args.build_dir and args.build_dir.exists():
        parser.error("--build-dir must be fresh")
    selected = None
    if args.plan or args.build_dir:
        try:
            selected = parameters(args.device, args.clock_hz, args.board_revision, args.verified_parameters)
        except ValueError as error:
            parser.error(str(error))
    from migen import Module, Signal
    from migen.fhdl import verilog
    from litex.soc.cores.spi.spi_bone import SPIBone
    import litex_boards.targets.adiuvo_forgix
    module = Module()
    counter = Signal(8, name="host_counter")
    module.sync += counter.eq(counter + 1)
    rtl = str(verilog.convert(module, ios={counter}))
    if "host_counter" not in rtl or "always" not in rtl:
        raise ValueError("Host RTL generation failed")
    report = {"schema_version": 1, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Host toolchain checks; no hardware opened or configured",
              "hardware_opened": False, "mcu_firmware_replaced": False,
              "versions": {name: importlib.metadata.version(name) for name in ("migen", "litex", "litex-boards", "mpremote")},
              "source_pins": json.loads(os.environ.get("FORGIX_TOOLCHAIN_PROVENANCE", "{}")),
              "rtl_sha256": hashlib.sha256(rtl.encode()).hexdigest(),
              "upstream_unverified_defaults": {"device": "T8F49C2", "clock_hz": 32000000, "clock_ball": "B4"},
              "physical_parameters": selected, "checks": []}
    for executable in ("mpremote", "litex_server"):
        tool = shutil.which(executable)
        if not tool:
            raise ValueError("Enter the Forgix Nix shell before checking tools")
        check = command_check([tool, "--help"])
        report["checks"].append(check)
        if check["exit_code"] != 0:
            raise ValueError("A host CLI help check failed")
    vendor = vendor_layout(os.environ.get("LITEX_ENV_EFINITY"))
    report["vendor_installation_present"] = vendor is not None
    report["vendor_cli_verified"] = False
    report["license_compile_verified"] = False
    if vendor is not None:
        wrapper = shutil.which("forgix-efinity")
        if wrapper is None:
            raise ValueError("Nix Efinity runtime wrapper is missing")
        command = [str(vendor / "bin/python3"), str(vendor / "scripts/efx_run.py"), "--help"]
        if os.environ.get("FORGIX_INSIDE_EFINITY") != "1":
            command.insert(0, wrapper)
        check = command_check(command)
        # Private installation paths are deliberately omitted from the receipt.
        check["arguments"] = ["VENDOR_PYTHON", "VENDOR_EFX_RUN", "--help"]
        report["checks"].append(check)
        report["vendor_cli_verified"] = check["exit_code"] == 0
    if args.build_dir:
        if not report["vendor_cli_verified"]:
            raise ValueError("Vendor CLI smoke check must pass before compiling")
        report["gateware_images"] = gateware_build(selected, args.build_dir.resolve(), vendor)
        report["license_compile_verified"] = True
    report["compile_inputs_ready"] = bool(selected and report["vendor_cli_verified"])
    report["gateware_ready"] = bool(report.get("gateware_images"))
    report["status"] = "host_and_vendor_cli_ready" if report["vendor_cli_verified"] else "host_ready"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps(report, indent=2))
    return 2 if args.require_vendor and not report["vendor_cli_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
