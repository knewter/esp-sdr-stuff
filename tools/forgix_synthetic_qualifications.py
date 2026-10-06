"""Committed synthetic physical/loading qualification tuples.

Offline compiler, simulator and process tests must never populate this registry.
The registry is separately frozen; qualification covers all other execution
inputs, the exact immutable runtime, artifacts, finite profile and pause policy.

Entries (2026-10-06): one bounded RAM-only episode per offered rate (256, 1024,
2048 B/s; periods 2,000,000/500,000/250,000) on ARM002 (675080b drain fix) and
FPGA candidate-004. Basis: Efinix guide (T8F49 exists only in speed grade 2),
measured clock episode 005, independent SPI handoff review SAFE-TO-QUALIFY,
existing artifact/startup/lifecycle reviews. Residual risks and stop conditions
are recorded inside each private qualification receipt.

Rebound 2026-10-06 after episode 001: only the reviewed host collector
admission rate limit (a1c3c05) changed; device artifacts are unchanged.
"""
QUALIFIED = (
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', 'cdf5792e992ad3859f1b0e04a73ed7e62dda41e92ad55a1e22baaf586104e727', '25d3ad8c23adf841e088f8326abb545325b27c4c6146bb46a346526a4102b14e', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 2000000, 960, False, True),
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', '30732394a25f72ef08257889cf72ba083136b8e15b8b5c1e76a962d8da1dc0c0', '25d3ad8c23adf841e088f8326abb545325b27c4c6146bb46a346526a4102b14e', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 500000, 3840, False, True),
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', 'ac7f1cde23fdd6c6c7cb590208e1a32008a2f5ff60b6d8bb5bc7f4f3eb55b60b', '25d3ad8c23adf841e088f8326abb545325b27c4c6146bb46a346526a4102b14e', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 250000, 7680, False, True),
)
