# Read-only USB power-control assessment

**No currently usable, verified host-controlled electrical power-cycle route
was found.** The ESP32's hub control nodes are unwritable by the current
operator, `uhubctl` is absent, and hub switching capability cannot be determined
from the available cached descriptors. Actual VBUS removal and alternate power
paths were not measured. This partial investigation does not close a recovery
or physical power-cycle gate.

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

## Permissions and descriptor limit

| Object | Owner and mode | Current operator write access |
|---|---|---|
| USB2 hub `/dev/bus/usb/001/006` | root:root, 0664, no added ACL | No |
| USB3 peer hub `/dev/bus/usb/002/003` | root:root, 0664, no added ACL | No |
| `1-1.4:1.0/1-1.4-port3/disable` | root:root, 0644 | No |
| `2-3.4:1.0/2-3.4-port3/disable` | root:root, 0644 | No |
| ESP device `authorized` | root:root, 0644 | No |

Effective capabilities are zero. Standard cached descriptors are readable;
the USB2 hub's descriptor file is 59 bytes. `lsusb -v` reports that it could not
open both hub devices, and therefore does not retrieve the class-specific hub
descriptor or `wHubCharacteristics`. Per-port versus ganged/no switching remains
**unknown**, rather than a confirmed hardware limitation. Existing permissions
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

## Concrete next route

A suitably privileged operator can first perform **read-only** hub descriptor
inspection for hub `1-1.4` and companion `2-3.4`, obtaining
`wHubCharacteristics`. If individual switching is advertised, further work
needs narrowly scoped control access to the corresponding port 3 controls,
physical verification that VBUS and the ESP32 supply actually fall, and a
check that siblings remain powered. No switching command is justified as
recovery proof from the present evidence alone.

If that capability or verification is unavailable, the physical power-removal
step requires an operator disconnecting the ESP32's power path, with alternate
supplies/backpower excluded, or a separately verified electrically switched
supply. The current read-only, unprivileged host inspection cannot complete
that step autonomously.
