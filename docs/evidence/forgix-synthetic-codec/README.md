# Reviewed finite source and USB codecs

Offline preparation, October 4, 2026. The separate C and Python codecs pass
16 author test groups and six independent groups using actual native C with
nonrecovering UBSan. [Checks and source hashes](checks.json) bind the reviewed
bytes. The [wire contract](../../../firmware/forgix-synthetic-source/CODEC.md)
keeps 16-byte FPGA records separate from 512-byte USB frames.

Independent tests reconstruct little-endian fixtures and CRCs, check all three
finite profiles, full nonce binding, tick wrapping, atomic failure, all fragment
boundaries and retained suffixes. The original C encoder returned success with
corrupted bytes when output overlapped unread input fields. Its failed review is
retained privately. Copying the record before writes fixes all 31 tested overlap
positions; independent C tests cover seven record and four batch overlaps.

Repeat: `nix develop .#ci --command task forgix:synthetic:codec:test`.
No device, vendor compiler or transport ran. These codecs do not implement the
RP drain engine, USB collector, END accounting, recovery or physical admission.
A strict source gap fails delivery qualification; reconciled drops cannot become
a zero-loss result. Tasks remain open.
