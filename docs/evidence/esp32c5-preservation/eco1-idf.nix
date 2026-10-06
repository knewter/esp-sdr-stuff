# Scratch-only: ESP-IDF d930a386da (last master commit supporting ESP32-C5 ECO1/v0.x)
# built with the same nixpkgs-esp-dev revision the repo flake locks.
{ sha256 ? "sha256-MIikNiUxR5+JkgD51wRokN+r8g559ejWfU4MP8zDwoM=" }:
let
  espDev = builtins.getFlake "github:mirrexagon/nixpkgs-esp-dev/5287d6e1ca9e15ebd5113c41b9590c468e1e001b";
  pkgs = import espDev.inputs.nixpkgs {
    system = "x86_64-linux";
    # Scratch-only: esp-dev's old esptool 4.x Python closure pulls ecdsa.
    config.permittedInsecurePackages = [ "python3.13-ecdsa-0.19.1" ];
    overlays = [ espDev.overlays.default ];
  };
in
pkgs.esp-idf-full.override {
  rev = "d930a386dae78cfab75f313af3df67921e748fc4";
  inherit sha256;
  toolsToInclude = [ "riscv32-esp-elf" ];
}
