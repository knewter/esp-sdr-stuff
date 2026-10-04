# Prospective linked startup audit

This is a hardware-free, fail-closed audit of the distinct synthetic stream
RAM profile. It does not qualify the whole boot path or admit a load.

Add `tools/audit_forgix_synthetic_startup.py` without changing the existing
bridge helper or its policies. Require the exact successful stream manifest,
all six exported file hashes, complete committed builder input bindings,
the named `synthetic-stream` ELF policy, and the reviewed SDK/TinyUSB versions
and assembled SDK NAR. Inputs and output must be private, regular and free
of symlink ancestors; CLI output contains only a compact status/hash.

Recognize the same exact linked Thumb early-reset and initializer-loop
instructions already reviewed for the bridge. Bind their literal reset
addresses, masks and both reset initializer slots to actual loaded ELF bytes.
Derive GPIO1/2/3/4/5/19 function/pad/pull reset defaults from hash-bound SDK
headers. Refuse changed instructions, absent/duplicate slots, wrong metadata,
missing loadable bytes, changed source/export hashes or a different SDK NAR.
Tests will mutate actual recognized bytes and bindings and exercise private
path refusals. Existing bridge tests remain unchanged.

The receipt must explicitly report that GPIO, pad and PIO resets occur before
`main`, where the application watchdog is enabled. It must not infer external
levels, pull networks, prior FPGA image continuity, complete boot-ROM or
initializer control flow, electrical turnaround, physical timing, USB delivery
or recovery. Checked UID/watchdog/application ordering and the whole linked
artifact require their separate independent audit. Unexpected compiler
sequences require new review rather than a permissive fallback.

Run focused tests through a private Task recipe in the locked Nix shell.
Commit source before auditing the retained ARM artifact. Root retains
installation and all physical admission decisions.
