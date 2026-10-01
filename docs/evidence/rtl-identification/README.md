# Attached RTL-SDR identification

Evidence class: **Board capture**. Recorded October 1, 2026.

[Probe output](tuner.log) reports RTLSDRBlog Blog V4, Rafael Micro R828D and explicit Blog V4 detection. The installed library therefore recognizes this board's V4 configuration. [Metadata](capture.json) records the command and its limits. Device identifier is redacted.

Command: `rtl_test -t`. The tuner-specific test ends with “No E4000 tuner found” because this is an R828D. That line is not a reception failure and is not a passed sustained-stream test either.

No EEPROM was written. Sample-loss behavior, HF reception, frequency accuracy, antennas and decoding remain untested. The 2.048 MS/s line is a configured rate, not a delivered-throughput measurement.
