# Independent matched-gain replay

Unchanged decoding reproduced **one fresh owned packet in 1,010 manual48
snapshots**, guarded ON0; hardware gain produced **zero in 984**, plus one
foreign CRC packet with payload redacted.

Independent measured-phase re-slicing, whitening and reflected CRC24 verified
the complete owned AD and packet window. All 1,994 transport records and both
full original-flash restorations passed. [Checks](checks.json) bind receipts;
see the [physical evaluation](../ble-matched-gain-001/README.md).

Partial ten-bit evidence: no RF denominator or calibrated gain. Three repeatable
responses and Trial B's original eight-bit/BW12/hardware prerequisite remain
unverified. Gates are unchanged.
