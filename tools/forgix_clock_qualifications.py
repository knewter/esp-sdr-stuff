"""Committed clock-measurement safety tuples.

A separately reviewed measurement may test nominal clock assumptions without
preclaiming measured clock/calibration. Offline tests never populate this set.

Entry 1 (2026-10-05): the 2026-10-04 independently reviewed safety candidate,
rebound to the current execution inputs after an independent diff review found
device behavior unchanged. Scope: ONE bounded RAM-only clock episode. Tuple:
uid, baseline, elf, manifest, bridge source, bitstream, contract,
qualification receipt, execution digest, environment digest.
"""
QUALIFIED=(
 ('155b9adf400cc003dccb6c80b818bc572df8c551d4cf0573b329b2ec6091af69',
  '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4',
  '07a2c748d59d53d25fd40bc12c1ef56731fd5c810d5f1a853b51ec26ace47533',
  '02100c7691836e15d5828992b70ea57629733594449026e5712f67997c12e6ab',
  '859cfcf143cdaef67427ee132e8f597b71831de1f4479b2f048726b3992d4071',
  '00cd8abc6bf31bc2210f6dca30b1cb287e9edcefc8ada78609fdbd03da7c3b80',
  '3790411b427af334c18fb534a18ad114f4980b7422d93e2de73935ba4a2d5b5e',
  '0633b6c9c74d8bc55c69885117305da7b3389419e74e5da041fe596af6081e83',
  '72d67d5d2ef16892ee0fa661e68c5f99d9f0a6719e1e0449b6cdb50992c44d9f',
  '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3'),
)
