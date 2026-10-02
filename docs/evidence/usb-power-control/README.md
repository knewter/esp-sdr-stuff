# Read-only USB power-control assessment

**Electrical power-cycle proof remains open.** The native user cannot access
hub controls, but a later narrowly scoped container successfully read the
class descriptors: both USB2 and USB3 hubs advertise individual port switching.
No power switch was operated and no actual VBUS or ESP32 rail voltage was
measured. The advertised feature supplies a candidate control route, rather
than proof of electrical removal.

The [sanitized receipt](receipt.json) records the read-only observations on
2026-10-01. No serial handle was opened, no USB reset/authorization command was
sent, no sysfs attribute was written, and no port power was switched. Public
VID/PID values and necessary USB topology paths are retained; serial numbers,
network addresses and host identifiers are omitted. USB device numbers are
transient and must be rechecked before any subsequent operation.

## Target and shared effects

The ESP32's `10c4:ea60` CP2102 is device path **`1-1.4.3`**, on **port 3 of
hub `1-1.4`** (`0bda:5411`, Realtek RTS5411, device revision 1.36). The hub's
standard configuration descriptor says self-powered. The kernel confirms this
port's USB3 peer at **`2-3.4-port3`**, on companion hub `2-3.4` (`0bda:0411`).

The immediate hub's port 2 carries the RTL-SDR. Port 4 carries another hub with
a webcam, FTDI UART and wireless HID receiver. Its upstream hub also serves a
Stream Deck HID. Whole-hub or upstream switching would affect these paths.
The actual electrical grouping of power switches is unknown, so a port number
alone does not prove isolation from siblings.

## Initial native-user permissions and descriptor limit

| Object | Owner and mode | Current operator write access |
|---|---|---|
| USB2 hub `/dev/bus/usb/001/006` | root:root, 0664, no added ACL | No |
| USB3 peer hub `/dev/bus/usb/002/003` | root:root, 0664, no added ACL | No |
| `1-1.4:1.0/1-1.4-port3/disable` | root:root, 0644 | No |
| `2-3.4:1.0/2-3.4-port3/disable` | root:root, 0644 | No |
| ESP device `authorized` | root:root, 0644 | No |

The native process had zero effective capabilities. Standard cached descriptors are readable;
the USB2 hub's descriptor file is 59 bytes. `lsusb -v` reports that it could not
open both hub devices, and therefore does not retrieve the class-specific hub
descriptor or `wHubCharacteristics`. At this initial native-user checkpoint, per-port versus ganged/no switching
was **unknown**, rather than a confirmed hardware limitation. The later
container inspection below resolves the advertised capability. Existing permissions
do not provide a usable libusb or sysfs control path to this operator.

Both ports report `disable=0` and port runtime status `active`; the USB2 port's
link state is `suspended`. These readings establish no measured electrical
voltage. The companion port is not attached to a SuperSpeed device.

## Electrical removal requires separate proof

The [Linux port-power documentation](https://www.kernel.org/doc/html/latest/driver-api/usb/power-management.html#usb-port-power-control)
explains that a logically off port can retain VBUS through shared power wells
or charging circuitry; runtime status does not expose actual VBUS voltage.
The [sysfs ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-bus-usb)
specifies that `disable` controls VBUS only where the hub supports power
switching. USB authorization changes, driver unbinding, USB resets and runtime
suspend cannot independently demonstrate electrical removal from the ESP32.

The [uhubctl documentation](https://github.com/mvp/uhubctl#usb-30-duality-note)
requires consideration of both USB2 and USB3 virtual hubs and warns that some
hubs disconnect data while retaining VBUS. Its
[capability procedure](https://github.com/mvp/uhubctl#how-do-i-check-if-my-usb-hub-is-supported-by-uhubctl)
separates the advertised switching feature from a physical voltage/power test.
VID/PID alone cannot establish that this particular hub implementation cuts
power, or that its ports are electrically independent.

USB VBUS removal also requires checking that the ESP32 has no separate supply
or backpower through GPIO, debugger, UART or other wiring. Disappearance of the
CP2102 from enumeration does not establish that the ESP32 supply rail reached
zero. This investigation cannot inspect that physical wiring or voltage.

## Follow-up: narrowly scoped descriptor inspection

The host operator can access its Docker daemon. An existing immutable container
image with Python ran temporarily with `--network none --read-only --cap-drop ALL`.
Only the two revalidated hub nodes were mapped, to `/dev/esp-hub-usb2` and
`/dev/esp-hub-usb3`. USB control ioctls require read/write node access even for
these IN requests; no port-state-changing request was sent. No broad privileged
container, host-network access, serial handle or filesystem mutation was used.

The [reader](hub_descriptor_reader.py) permits only IN/class/device
GET_DESCRIPTOR transfers, using descriptor types 0x29 and 0x2a. It sends no
SET_FEATURE/CLEAR_FEATURE transfer. [The actual result](descriptor-followup.json)
records four ports, USB2 `wHubCharacteristics=0x00a9` and USB3 `0x0009`;
both advertise **individual** logical port power switching. Advertised
power-on delay is zero in both descriptors; this is not a measured voltage
settling time. The image ID and reader hash are retained for provenance.
[Independent review](../ble-controller-independent-review/README.md) reparses
the descriptor bytes and checks the read-only reader's ABI and hash.

This removes the inability to inspect class descriptors. It does not establish
that the particular hub cuts VBUS, that no ESP32 alternate supply exists, or
that sibling power remains isolated under an actual switching operation.

## Concrete next route

The descriptors now support investigating scoped port-3 switching on both
virtual hubs. Acceptance still requires physical verification that VBUS and
the ESP32 supply fall, with sibling isolation and alternate supplies checked.
No actual switching or restoration power-cycle result is claimed here.

Without that electrical verification, the remaining proof needs the user's
confirmed removal/reapplication of the ESP32's power path, with alternate
supplies/backpower excluded, or a separately verified switched supply.
