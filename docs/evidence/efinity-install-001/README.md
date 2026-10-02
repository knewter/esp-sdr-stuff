# Actual Efinity installation and Nix runtime

On 2026-10-02 the completed Linux Efinity **2026.1.132** archive was copied
through the repo Task into permanent ignored `.vendor/efinity/` storage. The
versioned installation passed layout/hash checks, and repeating the install
reused the same selected release. Original Downloads files remain available.
The archive is 998,122,197 bytes, SHA-256
`8b09bf853cb4c586ef166ae0fc07e8753f58288f7d640b94a236f708f7a069e9`.

| Actual operation | Result | What it proves |
| --- | --- | --- |
| Completed full-release import and extraction | Pass | Local versioned installation exists |
| Repeated installation of the same release | Pass, reused | Selection is repeatable without another extraction |
| `forgix:efinity:check` | Pass | Real vendor Python and `efx_run.py --help` work through Nix FHS |
| `forgix:check -- --require-vendor` | Pass | Pinned host tools and vendor CLI work with automatic local selection |
| Corrected host alias: all host/vendor help checks inside FHS | Pass | Host tools and vendor child tools coexist |
| Initial pinned host Python inside vendor runtime | Failed, exit 1 | Vendor Python settings broke host standard-library startup |

The initial host-runtime failure is retained in private vendor logs. Its
`encodings` failure led to a scoped fix: `@forgix-python` removes vendor
`PYTHONHOME`/`PYTHONPATH` after setup for the explicit host process and its
children, then uses pinned Nix Python with `-E -s`. Other vendor settings and
`HOME` remain intact. Ordinary vendor help uses its original environment.
[Installer review](../efinity-bootstrap-independent-review/README.md) records
separate offline safety checks; [host-runtime fix review](../efinity-host-python-independent-review/README.md)
independently accepts the corrected alias and actual full runtime smoke; [setup instructions](../../research/forgix-toolchain.md)
provide the public Task commands.

These operations opened no hardware and changed no MCU or FPGA firmware.
There was **no licensed compilation or FPGA programming**. Physical FPGA
parameters remain unconfirmed. CLI help does not establish licensing or
compiler compatibility. The bundled instructions did not establish a universal
license variable or filename, so none was invented; the
[official Support Center](https://www.efinixinc.com/support/) describes the free
license request workflow. Actual compiler execution remains a separate proof. Vendor setup reported a
libstdc++ compatibility warning; the installed archive was retained without
removing its bundled library. That warning has not been tested by a compile.

[Sanitized results](results.json) contain software provenance and explicit
scope. Vendor binaries, opaque licenses, raw vendor logs and private paths
remain excluded from Git, the site and Nix store.
