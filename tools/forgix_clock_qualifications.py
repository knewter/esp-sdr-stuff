"""Committed clock-measurement safety tuples.

A separately reviewed measurement may test nominal clock assumptions without
preclaiming measured clock/calibration. Offline tests never populate this set.

History: entry 1 (2514834) admitted the 2026-10-04 reviewed candidate rebound
to current inputs; its episode 002 measured but lost half its reply to an
early reboot. Entry 2 (54a79a9) bound the same reviewed safety scope and identical
FPGA bitstream to ARM004, whose only change is the reviewed TinyUSB drain fix
(dabdd78); episode 004 then raced its post-reply identity check against the
finite reboot. Entry 3 (this) binds ARM005 (f2e5622: stay enumerated until the
host closes). Scope: ONE bounded RAM-only clock episode. Tuple: uid, baseline,
elf, manifest, bridge source, bitstream, contract, qualification receipt,
execution digest, environment digest.
"""
QUALIFIED=(
 ('155b9adf400cc003dccb6c80b818bc572df8c551d4cf0573b329b2ec6091af69',
  '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4',
  '15ee3c7df60a9daa764aaa4dc45205d2193954acb3964ddda942031fa79a94be',
  '45328354a3210e8da53cac14033f6dcf782bab8345673ed3db5a0f342bd95cfe',
  'c8da0ac97311d368b3e7f80cb7f7b5a4cc21f0cf474e164eeb54ddd3cb54a107',
  '00cd8abc6bf31bc2210f6dca30b1cb287e9edcefc8ada78609fdbd03da7c3b80',
  '3790411b427af334c18fb534a18ad114f4980b7422d93e2de73935ba4a2d5b5e',
  'fc2522df72c5b22f1cf381f24e1a72e55f6908592bd28bf6ac6640e76dc6b1d0',
  '7f374467971b887681f848024a04c2f36cbf4b6a70887a75241211b88d8ae0ab',
  '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3'),
)
