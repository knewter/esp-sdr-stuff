# Host BLE controller did not provide the required source count

The current Intel host controller accepted the owned advertising commands but
did not deliver an Advertising Set Terminated event in three bounded trials.
This source therefore cannot yet supply a verified transmitted-event denominator
for the ESP burst evaluation. This is a source-control limitation, not evidence
that the ESP cannot receive BLE. No receiver trial was performed for these three
counted-source attempts.

Root operated the hardware. This analysis read the resulting sanitized logs and
primary source documents only; it made no controller, serial, event-mask or
power changes. The physical receipts are published separately under
[the counted-source evidence](../evidence/ble-counted-source-smoke/).

## What the trials actually established

All trials used the same audited helper SHA-256
`50bdcec8491626ad0ba2628cf776ad49c8f0b2188f6431fab454b4f3cc69723f`:
one set on handle `0xEF`, legacy LE1M, nonconnectable/nonscannable properties
`0x0010`, primary channel map `0x01` (channel 37), and the owned 16-byte AD marker.
Duration was zero; the requested event limit was nonzero. Each trial performed
one enable, without automatic restart or fallback.

| Requested limit | Requested interval | Bounded termination wait | Observed termination events |
| --- | --- | --- | --- |
| 255 | 20 ms | 12.65 s | 0 |
| 10 | 20 ms | 5.30 s | 0 |
| 10 | 100 ms | 6.10 s | 0 |

Parameters, data, enable, own-set disable and own-set removal each received
status zero. The helper recorded `event_timeout`, an unverified controller
count, successful cleanup, and socket closure for every trial. The independent
dumpcap monitor also recorded all five commands and five successful command
completions, with no termination event. Its capture windows were approximately
20.15, 15.14 and 15.18 seconds, respectively. Root separately checked BlueZ
powered state and zero active advertising instances before and after.

The recorded limit is an instruction, not an observed count. Successful command
completion alone proves neither transmission nor the number of radiated packets.
Absence from both readers weakens a source-socket filtering explanation, but
dumpcap/libpcap cannot establish a loss-free Bluetooth monitor capture.

## Expected Linux mask, and what remains unknown

The installed kernel identifies as `7.1.9-1-MANJARO`. Root read cached controller
features `ff 59 00 08 00 00 00 00` and public USB VID/PID `8087:0029`.
The upstream stable [v7.1.9 HCI header](https://github.com/gregkh/linux/blob/v7.1.9/include/net/bluetooth/hci_core.h#L2026)
defines extended advertising capability from LE feature byte 1, bit `0x10`;
`0x59 & 0x10` is nonzero.

The corresponding [v7.1.9 initialization code](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_sync.c#L4531)
sets `events[2] |= 0x02` when that capability exists. This is LE event-mask
bit 17, enabling Advertising Set Terminated. Its
[base event-mask initialization](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_sync.c#L4302)
also enables LE Meta events for an LE-capable controller. Thus omission of
termination from normal upstream kernel initialization is not supported by
these features. This is an expectation from upstream source, not a measurement
of the running Manjaro controller's current mask or proof of its initialization
command's success.

The [Bluetooth HCI specification](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html)
defines LE Set Event Mask (`0x2001`, section 7.8.1) and requires the enclosing
LE Meta event to be enabled too. Bit 17 selects Advertising Set Terminated.
It defines no standard Read LE Event Mask or Read Event Mask command. The
default LE mask enables only bits 0–4; that default cannot be substituted for
the host's current configured mask.

The inspected v7.1.9
[controller structure](https://github.com/gregkh/linux/blob/v7.1.9/include/net/bluetooth/hci_core.h)
and [debugfs implementation](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_debugfs.c)
provide no current standard event-mask cache/readout. Root's actual debugfs
filename inventory likewise had no mask entry. Cached supported features and
commands are capabilities, not the current controller mask. The Intel driver's
[similarly named function](https://github.com/gregkh/linux/blob/v7.1.9/drivers/bluetooth/btintel.c#L174)
sends vendor opcode `0xFC52` for Intel-specific events; its bytes are not the
standard LE mask and cannot serve as a restoration baseline.

## Restoration requirement and remaining hypotheses

An exact reversible mask experiment would first need the previous eight-byte
LE mask from a successful write, established by a continuous trace with no
later unseen writes. It could then change only bit 17, acknowledge the write,
and restore the identical saved bytes in cleanup while detecting concurrent
mask writes. If the base LE Meta bit were also changed, its separate original
eight-byte mask would need the same treatment. No such baseline was captured
here, and no supported standard readback was found. Reconstructing a likely
kernel mask or writing all ones would not provide exact restoration. Resetting,
powering off, or detaching kernel ownership would introduce broader state
changes. None was performed or is proposed as a local workaround.

The actual mask might differ from the expected initialization mask. The
controller firmware might handle the legacy-PDU limiter or termination event
incorrectly, or another unmeasured scheduling/transport condition could matter.
These are hypotheses, not diagnoses. The two smaller-limit attempts also
failed, so this is not an observed failure confined to the value 255 or to the
20 ms interval. No current-mask mutation, firmware update, vendor diagnostic,
duration-limited comparison, reset, or alternative-PDU comparison was tested.

The primary specification's nonzero event-limit and termination rules support
the intended method, including sets configured for legacy PDUs through the
Extended Advertising API. They do not establish that this controller fulfilled
those rules. The mirrored original
[Core v5.2 PDF](https://faculty-web.msoe.edu/johnsontimoj/EE4980/files4980/Core_v5.2.pdf),
Vol 4 Part E sections 7.8.56 and 7.7.65.18, describes maximum-event termination
and its reported completed count; no legacy-PDU exception is stated there.
The missing observed event leaves the source-count gate open.

## Input needed before another counted receiver trial

Use a source/reference that independently supplies an auditable count: for
example a BLE transmitter with a verified completed-transmission counter plus
an independent reference receiver, or a separately captured reference trace
that accounts for the owned single-channel emissions. An FPGA could help only
after its RF interface, BLE waveform, transmitted count and reference capture
are validated; ownership of an FPGA alone supplies no RF count.

Establish the count and source timing before the next ESP trial, retain separate
ESP capture/CRC/owned-payload evidence, and label any controller-reported count
separately from independently observed radiation. The present results supply
neither count and do not justify replacing a measured success rate with the
requested number of events.
