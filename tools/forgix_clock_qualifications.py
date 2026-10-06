"""Committed clock-measurement safety tuples.

A separately reviewed measurement may test nominal clock assumptions without
preclaiming measured clock/calibration. Offline tests never populate this set.

History: entry 1 (2514834) admitted the 2026-10-04 reviewed candidate rebound
to current inputs; its episode 002 measured but lost half its reply to an
early reboot. Entry 2 (this) binds the same reviewed safety scope and identical
FPGA bitstream to ARM004, whose only change is the reviewed TinyUSB drain fix
(dabdd78). Scope: ONE bounded RAM-only clock episode. Tuple: uid, baseline,
elf, manifest, bridge source, bitstream, contract, qualification receipt,
execution digest, environment digest.
"""
QUALIFIED=(
 ('155b9adf400cc003dccb6c80b818bc572df8c551d4cf0573b329b2ec6091af69',
  '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4',
  '00e915cfc1b249c5015cd18e6a012013977845130fb2275fb00badffc671fbe9',
  '04e1e0f3bbab03efb1d6688c39f82deea910bc9cd9030f21a5236c85e03f800b',
  '9666b6f80642dc1b4ec8e2f7e64c2f207b4f6d2b86eb67317eeabbfa1664f87e',
  '00cd8abc6bf31bc2210f6dca30b1cb287e9edcefc8ada78609fdbd03da7c3b80',
  '3790411b427af334c18fb534a18ad114f4980b7422d93e2de73935ba4a2d5b5e',
  'e0bff97695baf137246c6aeffc07323424f85610ed5837a3696fa42907616667',
  'd53d469c1fff5a2519bb0783e0ba92d1d6870afbfe9ad8bef91a56917708f66e',
  '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3'),
)
