# Published repeatable ESP demo — October 2, 2026 UTC

The reviewed Nix-built Task demo is published at
[GitHub Pages](https://knewter.github.io/esp-sdr-stuff/), verified against exact
commit `18cca9036d301d80959c8b6f52c1161bca145f4d`.

- [Exact-commit workflow](workflow.json): GitHub build and deploy passed;
  the production Task checks include 280 unit tests and 13 browser groups.
- [Live browser checks](browser-checks.json): all 13 groups pass, including
  receipt-driven demo metrics, actual images, restoration/setup links, mobile
  layout and proposal navigation.
- [Complete immutable source comparison](source-checks.json): all **543**
  exported files, **11,144,861 bytes**, match the independently checked clean
  production build byte-for-byte. The deployed revision was checked before
  and after the comparison.

This closes demo publication task 3.2. [Session 005](../esp-demo-session-005/README.md)
and [session 006](../esp-demo-session-006/README.md) establish the two consecutive
physical minutes and full-flash/reset-boot restoration;
[independent review](../esp-demo-independent-review/README.md) reproduces those
checks. Site tests and browser screenshots are host evidence. Publication
does not add an RF, burst-reliability or FPGA performance result. The three
failed demo trials remain visible. No long-run reliability rate is inferred.

Reproduction: `nix develop .#ci --command task check:pages`,
`nix develop --command task browser:live`, and byte comparisons of the
published `source/<commit>/<path>` files with the corresponding clean build.
The workflow must succeed for the exact claimed commit. This receipt remains
a record of that deployment even when later commits supersede the live site.
