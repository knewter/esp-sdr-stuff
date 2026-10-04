"""Separate committed synthetic physical/loading qualification tuples.

Offline compiler, simulator and process tests must never populate this registry.
The registry is separately frozen; qualification covers all other execution
inputs, the exact immutable runtime, artifacts, finite profile and pause policy.
"""
QUALIFIED = ()
