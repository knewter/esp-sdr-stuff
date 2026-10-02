{ pkgs }:
let
  lib = pkgs.lib;
  ps = pkgs.python313Packages;
  litex = ps.buildPythonPackage {
    pname = "litex";
    version = "2026.08";
    pyproject = true;
    src = pkgs.fetchFromGitHub {
      owner = "enjoy-digital"; repo = "litex";
      rev = "8c01073afb71aa0a0709f02f8e24247589e8f5e4";
      hash = "sha256-4ChnvgXxDkq6+fkS20g4f0dgUXNgZ/AzTGiSAPT5dJs=";
    };
    build-system = [ ps.setuptools ];
    dependencies = [ ps.migen ps.packaging ps.pyserial ps.requests ];
    pythonImportsCheck = [ "litex" "litex.soc.cores.spi.spi_bone" ];
    # Hardware/toolchain-dependent upstream suites are not host smoke tests.
    doCheck = false;
  };
  boards = ps.buildPythonPackage {
    pname = "litex-boards";
    version = "2026.08";
    pyproject = true;
    src = pkgs.fetchFromGitHub {
      owner = "litex-hub"; repo = "litex-boards";
      rev = "10debf146d433ce8ac8aedcac84e97d252ff4d5b";
      hash = "sha256-hbUn+Db8mbDLGdGjRtAQNEYU8Y1W2wHqZ4/HeDYTdtk=";
    };
    build-system = [ ps.setuptools ];
    dependencies = [ litex ];
    pythonImportsCheck = [ "litex_boards.platforms.adiuvo_forgix" "litex_boards.targets.adiuvo_forgix" ];
    doCheck = false;
  };
  mpremote = ps.buildPythonPackage {
    pname = "mpremote"; version = "1.29.0"; pyproject = true;
    src = pkgs.fetchPypi {
      pname = "mpremote"; version = "1.29.0";
      sha256 = "ab0b6f21059698e573ca076fe9a0299e5fe7bbc3ca3f5b2f00007e22e51c7b80";
    };
    build-system = [ ps.hatchling ps.hatch-requirements-txt ps.hatch-vcs ];
    dependencies = [ ps.pyserial ps.platformdirs ];
    pythonImportsCheck = [ "mpremote" ];
  };
  testSource = pkgs.fetchFromGitHub {
    owner = "enjoy-digital"; repo = "aduivo_forgix_test";
    rev = "e7c71b750ca61690a70bc79ebd6ff5fbc65cedad";
    hash = "sha256-ZIylyJ5tqew94lgJi5tWe7W/jmFotkAPi4t8lQpzi78=";
  };
  python = pkgs.python313.withPackages (_: [ ps.migen litex boards mpremote ps.setuptools ]);
  # Runtime-provided licensed installation, never credentials/license files in
  # a world-readable store derivation. Does not download or install Efinity.
  efinityRuntime = pkgs.buildFHSEnv {
    name = "forgix-efinity";
    targetPkgs = p: [
      python p.bash p.coreutils p.gnumake p.gcc p.stdenv.cc.cc.lib p.zlib
      p.libusb1 p.libusb-compat-0_1 p.ncurses5 p.libffi p.openssl p.sqlite p.dbus
      p.libx11 p.libxext p.libxrender p.libxtst
      p.libxi p.libxcb p.libxcb-cursor p.libxft
      p.fontconfig p.freetype p.glib p.nss p.alsa-lib p.libxkbcommon p.libglvnd
    ];
    runScript = pkgs.writeShellScript "forgix-efinity-runtime" ''
      set -eu
      if [ -z "''${LITEX_ENV_EFINITY:-}" ] || [ ! -f "$LITEX_ENV_EFINITY/bin/setup.sh" ]; then
        echo "Set LITEX_ENV_EFINITY to your licensed Efinity installation" >&2
        exit 2
      fi
      source "$LITEX_ENV_EFINITY/bin/setup.sh"
      export FORGIX_INSIDE_EFINITY=1
      if [ "$#" -eq 0 ]; then
        exec bash --noprofile --norc
      fi
      exec "$@"
    '';
  };
  hostCheck = pkgs.runCommand "forgix-host-tools-check" { nativeBuildInputs = [ python ]; } ''
    export PYTHONNOUSERSITE=1
    export PYTHONPATH=
    python - <<'PY'
    import importlib.metadata
    from migen import Module, Signal
    from migen.fhdl import verilog
    from litex.soc.cores.spi.spi_bone import SPIBone
    from litex_boards.platforms import adiuvo_forgix
    import litex_boards.targets.adiuvo_forgix
    import mpremote.main
    module = Module()
    counter = Signal(8, name="host_counter")
    module.sync += counter.eq(counter + 1)
    rtl = str(verilog.convert(module, ios={counter}))
    assert "host_counter" in rtl and "always" in rtl
    assert importlib.metadata.version("mpremote") == "1.29.0"
    print("Host imports and independent counter RTL generation passed; no hardware or Efinity invoked")
    PY
    mpremote --help > mpremote-help.txt
    litex_server --help > litex-server-help.txt
    cp -r ${testSource} upstream-tests
    chmod -R u+w upstream-tests
    cd upstream-tests
    python -m unittest discover -s tests
    mkdir -p $out
    cp ../mpremote-help.txt ../litex-server-help.txt $out/
  '';
in {
  inherit python litex boards mpremote testSource efinityRuntime hostCheck;
  shell = pkgs.mkShell {
    packages = [ python pkgs.go-task pkgs.iverilog pkgs.verilator pkgs.yosys efinityRuntime ];
    PYTHONNOUSERSITE = "1";
    PYTHONPATH = "";
    PIP_REQUIRE_VIRTUALENV = "true";
    FORGIX_TEST_SOURCE = "${testSource}";
    FORGIX_PYTHON = "${python}/bin/python3";
    FORGIX_TOOLCHAIN_PROVENANCE = builtins.toJSON {
      litex = "8c01073afb71aa0a0709f02f8e24247589e8f5e4";
      boards = "10debf146d433ce8ac8aedcac84e97d252ff4d5b";
      migen = ps.migen.version;
      mpremote = "1.29.0";
      upstreamTests = "e7c71b750ca61690a70bc79ebd6ff5fbc65cedad";
      efinity = "Runtime installation required; not bundled or licensed by this shell";
    };
  };
}
