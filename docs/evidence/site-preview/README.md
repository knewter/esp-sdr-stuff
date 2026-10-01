# Research site browser verification

Evidence class: **Host capture**, not RF reception or FPGA measurement.

Captured October 1, 2026 from the built site at source revision
`9dcefac6bc7c8db2e19ddfeb185bbb008f563ea2` using Chromium and Playwright.
[Metadata](capture.json) records the full revision, time and checks.

Reproduce with `python3 tests/site_browser.py --url http://localhost:4321` after
a successful local build and static preview. Desktop/mobile navigation,
overflow, calculator, theme, seven proposal cards, deep links, image loading,
dialog focus and the boot-log link pass. The original stable snapshot URL
still opens its archived record. Actual BLE and RDS evidence images load.
There are no page errors or local HTTP failures.

![Desktop overview](overview-desktop.png)

![Mobile overview](overview-mobile.png)

![Proposal dialog](proposal-dialog.png)

![Design illustration gallery](design-gallery.png)

The gallery screenshot displays an explicitly labeled design illustration.
These images show the tracking website, rather than proving radio reception.
The board separately records one accepted snapshot experiment, five active
evaluations with physical gates, and AtomVM deferred by user.
