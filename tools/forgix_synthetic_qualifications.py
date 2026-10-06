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
"""
QUALIFIED = (
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', '5adaccca4ab21b1087130af0459e0359cad895f75c199482adadb6e1f9500087', '4bb1994b5b33b8b9ccb50eec374b69791c2934a45f4f9ee2baa40c67be4add94', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 2000000, 960, False, True),
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', 'fa2c1fcad58e1f162ee8a499cac64c066e6a793fa1fa6ee410051c39a2bd7360', '4bb1994b5b33b8b9ccb50eec374b69791c2934a45f4f9ee2baa40c67be4add94', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 500000, 3840, False, True),
 ('f2c7686f069c511deb82c0ba78da08dfb0a099182290cb6e42ecbdadd1e0981f', '19270836f36628179fe4f90caeccda9f61115acb49646530be915698fca3e66b', '2de852e2c3c5c39d2816a5236825e9c72d2c6a029128e0c1282def20b432f3be', 'b2ecd1643510a107f6ee9eb74e3616e011fb8c6eb9663e15bb3e6babd4b25919', 'da02fbce024a2c4869dd8feaff8117a6759292e434ceb3f302cb7fd0b762c68b', '4bb1994b5b33b8b9ccb50eec374b69791c2934a45f4f9ee2baa40c67be4add94', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', 250000, 7680, False, True),
)
