"""Committed backend/artifact qualification tuples.

Keep separate from backend source so binding its hash does not require a
self-referential hash. Entries need physical qualification and an independent
whole-backend loading/recovery review, not injected test receipts. The
production coordinator freezes this module with all execution inputs.

Entry 1 (2026-10-06): ONE bounded RAM-only register episode (FPGA task 3.4) on
configuration artifact 007 and register candidate-003. Basis: Efinix guide
(T8F49 exists only in speed grade 2), measured clock episode 005, independent
review of the register bitstream handoff (same guard/pins as the synthetic
image that ran on hardware) and of the post-FINISH fix. Tuple order: elf,
manifest, bridge source, bitstream, qualification, backend, coordinator,
execution, environment, uid, baseline.

Rebound 2026-10-06 after register episode 001 (FPGA configured, ARM exchange
timed out on host admission cost): worker admission rate-limit only.
"""
QUALIFIED=(
 ('0aa487f1fac4a8604166bda86e32b4931272447ba77accb45b529fdba5501b9c', '0972cc0b7f495c5c5d4e1b70b3bf438f4da7e5318d5230b9bb8a987d104c241e', 'd8a60ef5a586110b5714ace76b7d70dbf38d972a5a4b6138515c17ea267b2abb', 'cfeea136b92c4d93d7f0ba5a1b5f3f50859e56bb0ad1ff4f8ae0a177d7ff4975', '21f146d3c5f692a6e5b0c20bfaffb9281eb26cff56c8c04a71dcfe15ac52ce8e', '0d7d80b7a440999db2019a4908c3b25ced147810f4b585ef7b58faab4c032bf3', '9452ce914344b34a7ea9b22348c19b90c3a4795905d3defb301500567edec109', 'af083df0ffd7ed993384d6f5bf657761d380c114a65549995c77f2574340e811', '35992868daadcf2312c9432674e5efc9a5fb8eca6bb0377002800e9f9aa650e3', '155b9adf400cc003dccb6c80b818bc572df8c551d4cf0573b329b2ec6091af69', '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4'),
)
