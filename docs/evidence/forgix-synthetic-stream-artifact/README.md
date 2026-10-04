# Actual finite RP stream image passes offline review

October 4, 2026. The distinct RAM-only RP stream image embeds all 173,380 bytes
of the fourth synthetic FPGA candidate. Independent review checks every frozen
source and staged file, compiler/SDK bindings, complete linked image, compiled
PIO words and the actual ordinary-SRAM layout. [Checks](checks.json) bind the
ELF and private review receipt.

Allocation is 220,200 bytes within the separate 256 KiB policy: 9,024 bytes of
engine state include the 8,192-byte immutable frame queue, with a 4,096-byte
stack and no heap/core1 stack. Six actual-ELF mutation groups reject altered
image, PIO words, queue geometry, watchdog/UID ordering, reset mask and
initializer pointers. Named-symbol checks and selected linked paths pass;
this is not complete indirect control-flow or boot-ROM proof.

Seven startup-audit groups pass. The actual linked reset instructions and unique
initializer slots match the pinned SDK; GPIO, pads and PIO reset before main.
Main enables its watchdog before checked UID/USB/engine initialization, but
pre-main startup is outside that watchdog. Prior FPGA image/pin continuity
cannot be assumed. No FPGA was programmed.

Build with `nix develop .#forgix-spi-bridge --command task forgix:synthetic:stream:build -- --candidate .scratch/QUALIFIED_OFFLINE_CANDIDATE --build .scratch/FRESH_BUILD --output .scratch/FRESH_ARTIFACT`.
Audit saved artifacts with `nix develop .#forgix-spi-bridge --command task forgix:synthetic:stream:startup:audit -- --artifact .scratch/SAVED_ARTIFACT --output .scratch/FRESH_AUDIT`.

Physical grade/clock/SPI timing and pin ownership, admitted identity-selected
loading/configuration/collection/recovery, fresh original-flash preservation,
independent host delivery and actual recovery remain gates. USB API acceptance
is not delivered throughput. Offline artifact success accepts no hardware task.
