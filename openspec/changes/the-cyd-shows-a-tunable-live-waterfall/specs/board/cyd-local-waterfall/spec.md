## Purpose

A stand-alone, touch-tuned waterfall on the CYD's own screen, built on the
unchanged ESP-SDR receiver path.

## ADDED Requirements

### Requirement: The screen shows a live waterfall

When no host session is active, the CYD SHALL draw successive spectrum rows
from its own receiver snapshots, with the tuned centre frequency shown on
screen.

<!-- UNVERIFIED: no CYD display build has run yet. -->

#### Scenario: Board idles after boot
- **WHEN** the CYD boots and no host command arrives
- **THEN** the waterfall updates and shows the centre frequency

### Requirement: Touch retunes the receiver

A touch on the on-screen controls or the waterfall SHALL retune the receiver,
and the displayed frequency SHALL follow.

<!-- UNVERIFIED: no touch retune has been observed. -->

#### Scenario: User taps a control
- **WHEN** the user taps a tuning control
- **THEN** the displayed centre frequency changes and new rows use it

### Requirement: The host protocol is unchanged

Host commands SHALL keep their existing replies and capture behaviour. A host
session SHALL pause the display until the host has been idle.

<!-- UNVERIFIED: protocol coexistence is untested on the display build. -->

#### Scenario: Host connects while the display runs
- **WHEN** the host sends SYNC, INFO and a capture command
- **THEN** the replies match the 550fade receiver and the display pauses
