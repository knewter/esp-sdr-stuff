# Distinct clock observer RAM USB v1 (prospective/offline)

PID4014/product Forgix Clock RAM observer v1, one direct TinyUSB owner.
Watchdog2s before checked UID, heap0/core1inactive/stack4096/no_flash/max120s.
No configuration or measurement before one complete checked128B command.
First nonempty command bytes consume the sole intent; partial/invalid commands
cannot be retried. All integers little endian, CRC32 reflected IEEE/zlib.

Command128:0 magic FGCQ;4 version1;5 operation1;6..7 zero;8..23 nonzero128bit
nonce;24..55 exact build SHA256;56..87 exact image SHA256;88..123 zero;
124..127 CRC32 over0..123. Completion strictly before boot+30s.
Config once: min(now+20s,boot+30s); observer only on config status0 and uncancelled
fresh admission; capture min(now+2s,boot+120s). Config drives shared DATA only
while FPGA unarmed/configuring. Period sampling remains input-only and one-shot.

Result512:0 FGCR;4 version1;5 type1;6..7 zero;8..23 nonce;
24..55 build;56..87 image;88 config statusU32;92 observer statusU32;
96 countU32;100..163 sixteen raw decrementU32 slots (unusedzero);
164 bootUsU64;172 complete-commandUsU64;180 configBeginUsU64;
188 configEndUsU64;196 captureBeginUsU64;204 captureEndUsU64;
212 replyEncodedUsU64;220 drainDeadlineUsU64;228 cleanupVerifiedU32;
232 configurationAttemptedU32;236..507 zero;508 CRC32 over0..507.
No success from partial output. This snapshot is encoded before USB enqueue;
USB accepted bytes do not prove host delivery. Drain min(encoded+2s,boot+120s).
No resend/flush-input/resync/second command or implicit register access.

Config status uses existing BRIDGE enum0..5; observer0..5 as observer.h.
Observer0 requires config0, exactly16 valid periods and cleanupVerified1.
Failure retains raw completed samples; status1/count0 is default unmeasured.
Untrusted/malformed/partial command has no trusted nonce and emits no result.
Timed/cancelled valid command may emit failed result after safe cleanup.
All success callbacks/clocks must remain strictly before stage/boot bounds;
clock callbacks can raise cancellation. Primary failure survives latercancel.

Command parser and reply codec alone do not admit hardware. Host requires
registered exact physical/loading/recovery assumptions, full UID/baseline/
source/runtime/artifact tuple and exclusive inherited flock/durable sharedlease.
Old registries/profilewhitelists unchanged. Complete preserved MCU factoryreturn
and independent raw replay precede any measurement acceptance. Relative ratio
only, no calibrated MHz, rails, physical margins or original task completion.
