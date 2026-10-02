{
  description = "Pinned tools for the ESP32 SDR evaluation; entering a shell never opens hardware";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/20b1ddd1aa5ace70c9468305030aa4f9ef79671b";
    openspec-src = { url = "github:Fission-AI/OpenSpec/v1.11.0"; flake = false; };
    pico-sdk-src = { url = "github:raspberrypi/pico-sdk/2.2.0"; flake = false; };
    redsea-src = { url = "github:windytan/redsea/4cc27df9939798e800c4ff7cb484be6d9bf68b4d"; flake = false; };
    liquid-dsp-src = { url = "github:jgaeddert/liquid-dsp/10041f70cebbe3b97887e75bb41e48b73dda1b23"; flake = false; };
    esp-dev.url = "github:mirrexagon/nixpkgs-esp-dev/5287d6e1ca9e15ebd5113c41b9590c468e1e001b";
  };

  outputs = inputs@{ self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      lib = pkgs.lib;
      node = pkgs.nodejs_22;
      pnpm = pkgs.pnpm_10;
      openspec = pkgs.stdenvNoCC.mkDerivation {
        pname = "openspec";
        version = "1.11.0";
        src = inputs.openspec-src;
        nativeBuildInputs = [ node pnpm pkgs.pnpmConfigHook pkgs.makeWrapper ];
        pnpmDeps = pkgs.fetchPnpmDeps {
          pname = "openspec";
          version = "1.11.0";
          src = inputs.openspec-src;
          inherit pnpm;
          fetcherVersion = 3;
          hash = "sha256-P50JVvLbTWl66/aOiEZgpAD8z/AAJmn1AoKiNCZbvi4=";
        };
        buildPhase = ''
          runHook preBuild
          node build.js
          runHook postBuild
        '';
        installPhase = ''
          runHook preInstall
          mkdir -p $out/lib/openspec $out/bin
          cp -a bin dist schemas node_modules package.json $out/lib/openspec/
          makeWrapper ${node}/bin/node $out/bin/openspec \
            --add-flags "$out/lib/openspec/bin/openspec.js"
          runHook postInstall
        '';
        doInstallCheck = true;
        installCheckPhase = ''
          test "$($out/bin/openspec --version)" = 1.11.0
        '';
      };
      siteDependencies = pkgs.buildNpmPackage {
        pname = "esp32-sdr-site-dependencies";
        version = "0.1.0";
        src = lib.fileset.toSource {
          root = ./site;
          fileset = lib.fileset.unions [ ./site/package.json ./site/package-lock.json ];
        };
        nodejs = node;
        npmDepsHash = "sha256-1x9Kfs1ZMG1k+OE702ocnvj8P7zYy9ypp3K0yMwltW4=";
        dontNpmBuild = true;
        installPhase = ''
          runHook preInstall
          mkdir -p $out
          cp -a node_modules $out/node_modules
          cp package-lock.json $out/package-lock.json
          runHook postInstall
        '';
      };
      picoSdk = pkgs.pico-sdk.overrideAttrs {
        version = "2.2.0";
        src = inputs.pico-sdk-src;
        sourceRoot = "source/tools/pioasm";
        cmakeFlags = [ "-DPIOASM_VERSION_STRING=2.2.0" ];
      };
      picotool = pkgs.picotool.override { pico-sdk = picoSdk; };
      picotoolImageTag = builtins.substring 0 16 (builtins.hashString "sha256" picotool.drvPath);
      picotoolImage = pkgs.dockerTools.buildLayeredImage {
        name = "esp-sdr-picotool";
        tag = picotoolImageTag;
        contents = [ picotool ];
        config = { Cmd = [ "${picotool}/bin/picotool" ]; };
      };
      liquidDsp = pkgs.liquid-dsp.overrideAttrs (old: {
        version = "1.8.3";
        src = inputs.liquid-dsp-src;
        # Both old Nixpkgs patches are already upstream at this revision.
        patches = [ ];
        cmakeFlags = old.cmakeFlags ++ [
          "-DCMAKE_INSTALL_LIBDIR=lib" "-DCMAKE_INSTALL_INCLUDEDIR=include"
        ];
      });
      redsea = pkgs.stdenv.mkDerivation {
        pname = "redsea";
        version = "1.3.1";
        src = inputs.redsea-src;
        # GitHub archives contain LFS pointer text; hydrate the two published
        # upstream test recordings using their audited LFS object SHA256s.
        postUnpack = ''
          cp ${pkgs.fetchurl {
            url = "https://media.githubusercontent.com/media/windytan/redsea/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/test/resources/mpx-testfile-yksi.flac";
            sha256 = "c92b9c72f132e37cbe253a19a6ae17c52f17f5318672c391ce7f3b9657320eb1";
          }} $sourceRoot/test/resources/mpx-testfile-yksi.flac
          cp ${pkgs.fetchurl {
            url = "https://media.githubusercontent.com/media/windytan/redsea/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/test/resources/rds2-minirds-192k.flac";
            sha256 = "9d2d83af603a70b2ef4e55084222550b79bf00613fe9c353e7916b325c3986a5";
          }} $sourceRoot/test/resources/rds2-minirds-192k.flac
        '';
        nativeBuildInputs = [ pkgs.meson pkgs.ninja pkgs.pkg-config ];
        buildInputs = [ liquidDsp pkgs.libsndfile pkgs.nlohmann_json pkgs.catch2_3 ];
        mesonFlags = [ "-Dbuild_tests=true" ];
        doCheck = true;
      };
      pythonBase = pkgs.python313;
      forgix = import ./nix/forgix-toolchain.nix { inherit pkgs; };
      bleMonitorImageTag = builtins.substring 0 16 (builtins.hashString "sha256" pkgs.wireshark-cli.drvPath);
      bleMonitorImage = pkgs.dockerTools.buildLayeredImage {
        name = "esp-sdr-ble-monitor";
        tag = bleMonitorImageTag;
        contents = [ pkgs.wireshark-cli ];
        config.Cmd = [ "${pkgs.wireshark-cli}/bin/dumpcap" ];
      };
      bleSourceImageTag = builtins.substring 0 16 (builtins.hashString "sha256" pythonBase.drvPath);
      bleSourceImage = pkgs.dockerTools.buildLayeredImage {
        name = "esp-sdr-ble-source";
        tag = bleSourceImageTag;
        contents = [ pythonBase ];
        config.Cmd = [ "${pythonBase}/bin/python3" ];
      };
      firmwarePkgs = import inputs.esp-dev.inputs.nixpkgs {
        inherit system;
        overlays = [ inputs.esp-dev.overlays.default ];
      };
      idfDriversGdb = pkgs.python313Packages.buildPythonPackage {
        pname = "idf-drivers-gdb";
        version = "0.1.1";
        pyproject = true;
        src = pkgs.fetchPypi {
          pname = "idf_drivers_gdb";
          version = "0.1.1";
          sha256 = "dc972dfb9b106b0b883b41bbf8c3ed9cbee8a97367c75eeeab772c573c8455c0";
        };
        build-system = [ pkgs.python313Packages.setuptools ];
        # These modules run inside GDB; SDK distribution checks run below.
        doCheck = false;
      };
      idfSbom = pkgs.python313Packages.buildPythonPackage {
        pname = "esp-idf-sbom";
        version = "1.4.0";
        pyproject = true;
        src = pkgs.fetchPypi {
          pname = "esp_idf_sbom";
          version = "1.4.0";
          sha256 = "578923c1d58f7e5c432780611d055ab163c64229a91a10807bac00bfb608c844";
        };
        build-system = [ pkgs.python313Packages.setuptools ];
        dependencies = with pkgs.python313Packages; [
          pyyaml schema license-expression rich pyparsing esp-pylib
        ] ++ pkgs.python313Packages.esp-pylib.optional-dependencies.cli;
        pythonImportsCheck = [ "esp_idf_sbom" ];
      };
      idfKconfig = pkgs.python313Packages.buildPythonPackage {
        pname = "esp-idf-kconfig";
        version = "3.13.0";
        pyproject = true;
        src = pkgs.fetchPypi {
          pname = "esp_idf_kconfig";
          version = "3.13.0";
          sha256 = "b79b8dca0aea087d99eeaae0e46266f791e3f19d01495d5da95e9a11e04869fc";
        };
        build-system = [ pkgs.python313Packages.setuptools ];
        dependencies = with pkgs.python313Packages; [ esp-pylib pyparsing textual ]
          ++ pkgs.python313Packages.esp-pylib.optional-dependencies.cli;
        pythonImportsCheck = [ "esp_kconfiglib" "kconfgen" ];
      };
      espIdf = (firmwarePkgs.esp-idf-xtensa.override {
        rev = "25fe69f946311abdaf9ad56591f25fedbc20ac98";
        sha256 = "sha256-WGTSV8xTVzuuRGN7ihp5k+v0do97r3d0vTzlyD9TegQ=";
        toolsToInclude = [ "xtensa-esp-elf" "esp32ulp-elf" ];
        python3 = pythonBase;
        # Update esp-dev's Python5.5 recipe to this SDK's core requirements.
        # Replace its old esptool constructor so recursive consumers also
        # receive one esptool5 module, avoiding conflicting Python closures.
        callPackage = file: args:
          if args ? pythonPackages then
            firmwarePkgs.callPackage file (args // {
              pythonPackages = args.pythonPackages // {
                buildPythonPackage = attrs:
                  if (attrs.pname or "") == "esptool" then
                    pkgs.python313Packages.toPythonModule esptool
                  else if (attrs.pname or "") == "esp-idf-kconfig" then idfKconfig
                  else args.pythonPackages.buildPythonPackage attrs;
              };
            })
          else firmwarePkgs.callPackage file args;
        extraPythonPackages = ps: [
          ps.rich-click ps.esp-pylib ps.construct idfDriversGdb idfSbom
        ] ++ ps.esp-pylib.optional-dependencies.cli
          ++ ps.esp-pylib.optional-dependencies.ide;
      }).overrideAttrs (old: {
        # Upstream's explicit phase does not invoke postInstall hooks.
        installPhase = lib.replaceStrings [ "cp -rv . $out/" ] [ "cp -r . $out/" ] old.installPhase + ''
          mkdir -p $out/bin
          makeWrapper "$out/python-env/bin/python3" "$out/bin/idf.py" \
            --add-flags "$out/tools/idf.py" \
            --set IDF_PATH "$out" --set IDF_PYTHON_ENV_PATH "$out/python-env" \
            --set IDF_COMPONENT_MANAGER 0 --set IDF_PYTHON_CHECK_CONSTRAINTS no \
            --set PYTHONNOUSERSITE 1 --unset PYTHONPATH
        '';
      });
      idfProvenance = pkgs.writeText "esp-sdr-idf-provenance.json" (builtins.toJSON {
        revision = "25fe69f946311abdaf9ad56591f25fedbc20ac98";
        idf_path = "${espIdf}";
        source_path = "${espIdf.src}";
        source_hash = "sha256-WGTSV8xTVzuuRGN7ihp5k+v0do97r3d0vTzlyD9TegQ=";
        packaging_note = "Nix fixed-output source with submodules; packaging updates script shebangs, strips original Git metadata and creates an emulated SDK version tag. SDK core Python requirements and compiler checked in the Nix shell. Archived artifact binary equivalence is not claimed.";
      });
      esptool = pkgs.esptool.override { python3Packages = pkgs.python313Packages; };
      pythonFull = pythonBase.withPackages (ps: with ps; [
        numpy scipy matplotlib dbus-next pyserial playwright (toPythonModule esptool)
      ]);
      nativeBleCryptoCheck = pkgs.runCommand "native-ble-real-psa-check" {
        nativeBuildInputs = [ pkgs.stdenv.cc pythonFull ];
        buildInputs = [ pkgs.mbedtls ];
        CC = "${pkgs.stdenv.cc}/bin/cc";
        NATIVE_PSA_CFLAGS = "-I${lib.getDev pkgs.mbedtls}/include";
        NATIVE_PSA_LIBS = "-L${lib.getLib pkgs.mbedtls}/lib -Wl,-rpath,${lib.getLib pkgs.mbedtls}/lib -lmbedcrypto";
        PYTHONNOUSERSITE = "1";
      } ''
        cd ${self}
        python3 -m unittest discover -v -s tests -p test_native_ble_reference.py
        mkdir -p $out
        printf '%s\n' 'Real mbedTLS PSA AES known-answer and alias tests passed; no hardware opened.' > $out/result.txt
      '';
      commonPackages = [
        node pkgs.go-task openspec pkgs.chromium pkgs.git pkgs.coreutils
        pkgs.ripgrep pkgs.curl pkgs.jq
      ];
      shellVariables = {
        SITE_NODE_MODULES = "${siteDependencies}/node_modules";
        CHROMIUM_EXECUTABLE = "${pkgs.chromium}/bin/chromium";
        PYTHONNOUSERSITE = "1";
        PYTHONPATH = "";
        PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";
        # No pip/global-npm/browser installation is needed by project tasks.
        PIP_REQUIRE_VIRTUALENV = "true";
      };
    in {
      packages.${system} = {
        inherit openspec picotool redsea;
        site-dependencies = siteDependencies;
        pico-sdk = picoSdk;
        liquid-dsp = liquidDsp;
        rtl-sdr = pkgs.rtl-sdr-blog;
        picotool-usb-image = picotoolImage;
        ble-monitor-image = bleMonitorImage;
        ble-source-image = bleSourceImage;
        forgix-python = forgix.python;
        forgix-efinity-runtime = forgix.efinityRuntime;
        forgix-upstream-tests = forgix.testSource;
        forgix-host-tools = forgix.hostCheck;
        esp-idf = espIdf;
        native-ble-crypto-check = nativeBleCryptoCheck;
      };
      checks.${system}.forgix-host-tools = forgix.hostCheck;
      checks.${system}.native-ble-crypto-check = nativeBleCryptoCheck;
      devShells.${system} = {
        forgix = forgix.shell;
        ci = pkgs.mkShell (shellVariables // {
          packages = commonPackages ++ [ pythonFull ];
        });
        default = pkgs.mkShell (shellVariables // {
          packages = commonPackages ++ [
            pythonFull esptool picotool redsea pkgs.rtl-sdr-blog
            pkgs.wireshark-cli pkgs.bluez pkgs.usbutils pkgs.psmisc pkgs.util-linux
            pkgs.cmake pkgs.ninja pkgs.gnumake pkgs.pkg-config pkgs.meson
            pkgs.docker-client pkgs.gh
          ];
          PICO_SDK_PATH = "${picoSdk}/lib/pico-sdk";
          PICOTOOL_USB_IMAGE = "${picotoolImage}";
          PICOTOOL_USB_IMAGE_TAG = "esp-sdr-picotool:${picotoolImageTag}";
          BLE_MONITOR_IMAGE = "${bleMonitorImage}";
          BLE_MONITOR_IMAGE_TAG = "esp-sdr-ble-monitor:${bleMonitorImageTag}";
          DUMPCAP = "${pkgs.wireshark-cli}/bin/dumpcap";
          BLE_SOURCE_IMAGE = "${bleSourceImage}";
          BLE_SOURCE_IMAGE_TAG = "esp-sdr-ble-source:${bleSourceImageTag}";
          BLE_SOURCE_PYTHON = "${pythonBase}/bin/python3";
        });
        firmware = firmwarePkgs.mkShell {
          packages = [ espIdf pkgs.go-task pkgs.git ];
          IDF_PATH = "${espIdf}";
          ESP_SDR_IDF_REVISION = "25fe69f946311abdaf9ad56591f25fedbc20ac98";
          ESP_SDR_IDF_PROVENANCE = "${idfProvenance}";
          PYTHONNOUSERSITE = "1";
          IDF_COMPONENT_MANAGER = "0";
          # Versions are locked by Nix instead of a mutable downloaded
          # constraints file. SDK core requirements remain checked by idf.py.
          IDF_PYTHON_CHECK_CONSTRAINTS = "no";
          PIP_REQUIRE_VIRTUALENV = "true";
        };
      };
      # The optional firmware shell pins ESP-IDF25fe69f9 and obtains tools
      # from that SDK's checksummed tools.json through Nix. The upstream
      # Python5.5 recipe is extended for this SDK's checked core requirements.
      # This environment does not assert archived firmware binary equivalence.
      # No ambient IDF installer/pip/compiler fallback is supported or implied.
      # The Forgix shell provides a runtime for a separately installed licensed
      # Efinity compiler; vendor installation/license files never enter the store.
      # Nix builds of replay tools need not reproduce old
      # host-compiler binary hashes; source pins and decoder output are checked.
    };
}
