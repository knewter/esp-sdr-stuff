# Independent interactive-demo replay

**PASS** for the [physical interactive run](../esp-demo-play-001/README.md)
on 2026-10-02. This reviewer did not author its demo/bridge or operate a
device. A separate, private stdlib parser replayed every saved binary packet
through locked Nix/Task; [checks.json](checks.json) binds inputs and results.

All **2,706 SPC1 spectrum frames and 225 SPS1 statistics frames** pass CRC32.
Sequence is consecutive; sample indices increase; every frame has eight FFT
windows, 4,096 processed pairs, the gap flag and mean-detector encoding.
Every CSV sequence, CRC, sample/gain field and power-code summary matches the
binary payload. Terminal totals equal 21,648 FFTs / 11,083,776 pairs. Host
60.005024284 seconds and firmware 60.005194 seconds both exceed the requested
minute. The largest consecutive host arrival gap is 0.036664479 seconds.
Nominal sampled coverage is **0.230893%**, with acquisition gaps.

The reviewed private install record and three actual binaries match the
[demo's exact part hashes](../esp-demo-play-001/demo.json); installation logs
contain three verified hashes. Both actual before-install and restored
4,194,304-byte reads match the preserved baseline. Restored boot bytes contain
the known original application, SDK and high/low GPIO markers; the restore
write log also confirms verification. This proves reset recovery, not physical
power removal.

Both actual viewer screenshots were inspected: live acquisition and terminal
2,706-frame / zero-CRC-failure state agree with the numerical evidence. They
show uncalibrated power codes and explicit snapshot-gap labels. Screenshots
prove the viewer, not signal identity or RF calibration.

The unchanged CSV and PNGs total **506,064 bytes** and remain private to keep
the existing site budget. Their exact sizes/hashes are retained in the receipt;
the public demo/restoration/summary receipts remain linked. No exported source
or size gate changed. Existing published demo visuals remain available.

Private replay: `nix develop .#ci --command task --exit-code -t
.scratch/esp-demo-review/Taskfile.yml replay` in the review worktree. Its Task
SHA is `82fd115544789eb78d5c6f97b64b31b78209063bb3ee8f0d340ad987c08a6f2c`.
The executed bridge SHA is
`e8c39db4f8e621011a7a92192f62246219604903e1a629aa899107cf1b880608`.
No serial, USB or other hardware operation was performed during review.
