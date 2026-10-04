# Pending register finalization blocks all Forgix routes

October 4, 2026: **author host checks pass; independent review pending**.
[Checks and hashes](checks.json) bind source `6bfcc5d`, the prospective
`dfaa101` plan, and the retained private proof. No physical acceptance is claimed.

Independent review of the earlier `54bda122` correction reproduced a release
failure after the active lease had already been removed. If lease recreation
also failed, durable pending evidence survived, but the synthetic operator could
still acquire its lock. The original failing receipt and unchanged effective
probe remain preserved; this checkpoint supersedes that admission behavior.

One shared predicate now refuses new Forgix admission, device selection, worker
dispatch, preservation and recovery whenever register-finalization evidence is
present. This includes malformed contents, directories and dangling links.
Inspection errors also refuse access; only confirmed absence permits it. The
USB, register and synthetic routes use the same predicate, including inherited
locks and contained workers. Closing and reaping already owned resources remain
available. Command whitelists, flash operations, lifecycle implementations and
all 49 tracked firmware files remain unchanged.

Locked Task checks passed 272 distinct host groups (286 raw, with the shared
runtime's 14 groups repeated), plus the original unchanged cross-route probe.
The checks exercise actual temporary flock ownership and pending-only failure,
serial-driver refusal before opening, cancellation/storage paths and harmless
owned-child cleanup. Current register admission covers 36 inputs and all 19
artifact build sources. Seven tool/archive bytes, all 268 Nix paths and their
1,097 reference edges were verified; 136 imported external Python files belong
to the closure. The shared synthetic source map is 65 inputs and needs a fresh
merged production freeze.

A real harmless inherited query child passed the actual worker admission using
fixture qualification, continuity and two full 2 MiB baseline copies. Its
parent retained its temporary local lock afterward. Production qualification
registries remain empty; these fixtures do not qualify a board or original flash.

The historical configuration003 artifact still fails the strict source guard.
After source review and merge, a fresh root-owned ARM build and independent
artifact review remain required. FPGA grade, electrical limits, clock, loading,
SPI timing and physical throughput remain unqualified. No hardware task was
checked and no board, Docker daemon, container, ARM compiler or vendor build was
used by these author checks. Loaded-image identity remains historical evidence;
current root endpoint/image/identity checks are separate. Live kernel,
filesystem, daemon and pre-Python/Task ancestor trust limits remain explicit.
