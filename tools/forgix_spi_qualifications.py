"""Committed backend/artifact qualification tuples; no hardware admitted yet.

Keep separate from backend source so binding its hash does not require a
self-referential hash. Future entries need physical qualification and an
independent whole-backend loading/recovery review, not injected test receipts.
The production coordinator must freeze this module with all execution inputs.
"""
QUALIFIED=()
