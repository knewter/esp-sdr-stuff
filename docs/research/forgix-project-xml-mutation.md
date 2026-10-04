# Synthetic compiler project XML verification — prospective correction

This is offline compiler preparation for FPGA task 2.1. Failed synthetic
candidate-002 remains failed. No resource fit, timing closure, physical load,
transport qualification or OpenSpec acceptance is granted by this correction.

The bounded compiler binds eleven committed source inputs and eight generated
inputs before compilation. Candidate-002 completed the four reported vendor
stages, but the exact project XML hash changed and its worker correctly refused
success. The other seven generated inputs and all eleven source inputs stayed
exact. Preserve the failed receipts and output before any replacement attempt.

The pinned Efinity 2026.1.132 runner's `update_project_file` parses the project,
sets its existing software version from `scripts/sw_version.txt`, and writes
through Python ElementTree. Its separate pruning function can remove historical
root metadata. The pinned LiteX generator includes a project location and generation date.
Only their explicitly verified removal plus an independently reproduced serializer rewrite with
unchanged requested version and complete unchanged semantic inputs may qualify.
No compiler, device or proprietary script is executed by the host tests.

Before implementation, independently regenerate the exact original XML with
the pinned LiteX generator, mocking its interface subprocess. Compare it with
candidate-002's retained post-compile bytes and the original hash in
`generated.json`. Freeze the complete original project bytes privately and
bind their hash. After compilation accept either byte-identical XML or exactly
the ElementTree serialization of that frozen original after removing only the
root location and generation-date attributes, with unchanged software version.
The original location must equal the owned gateware directory and the date must
match the pinned generator format. Refuse unexpected root metadata, including
last_run_tool, rather than silently prune it. Do not remove the project from the generated-input hash inventory,
ignore arbitrary attributes, collapse nodes, normalize filenames, reorder
options, or drop text/comments to conceal mutations. All other generated input
hashes and source hashes remain exact. Preserve both actual byte hashes and the
specific recognized rewrite in the replacement receipt.

Host regressions must exercise actual pinned XML generation and the whole
mocked worker/output verification path. Reject target/grade, source/library,
constraints/clock, top module, synthesis/route/bitstream/debug/security options,
extra/duplicate nodes, version drift, malformed/entity XML, modified frozen
original, and changes combined with the legitimate rewrite. Keep complete
post-compile validation, fresh stage/image checks, private modes and closure
requirements. A replacement real build and independent report/artifact review
remain root-owned future work.

The retained output also contains an empty auxiliary `.peri.cdo` report. The
bounded report inventory may retain an empty regular auxiliary file with its
zero byte count and SHA256. Critical generated inputs, console/stage logs and
bitstream remain nonempty. Empty reports still require single-link regular
files, no symlinks, bounded count/total bytes and exact private inventory.

Independent reproduction recovered candidate-002's original project hash
`e6451440f4a640eb9b8962ea1f67223246b7d9d1a9aa82be088c1790b02b0b13`
from the pinned generator and its original location/date. Removing those two
root attributes and serializing with ElementTree exactly reproduces retained
post-compile hash
`6a7dba78673aae8d1481f6f2f9d3462fec07a05a123925ad6de6154d5afe4a17`.
This is an independently regenerated diagnostic, not a recovered original copy
or a retrospective success receipt. No other node or attribute changed.
