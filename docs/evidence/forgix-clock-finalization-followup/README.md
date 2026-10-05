# Clock finalization software reviewed; fresh runtime pending

On October 5, the root operator refreshed the clock observer's read-only runtime
at `b37bd3989cdb35a7e06740c81f1264b720d3fe48`. All **88 execution inputs,
seven tools, 268 content-verified Nix paths and 1,097 reference edges** were
bound, with fresh local image inspection and whole archive checks. The operation
took 17.727 seconds internally and 18.458 seconds in its external Task observer;
both observed Task and parent exited0. Independent saved-only review verified
the whole tuple, 42 project imports, 177 root external imports, complete artifact
exports and unchanged 32 ARM/nine FPGA source inputs. Its four refusal controls
passed. This is runtime preparation, not a physical clock measurement or source
timing proof. New planning and correction code require a fresh execution binding.

The first attempt refused before runtime selection completed because its Nix
shell omitted a required tool. Its observed Task exit201, source, log and exact
Taskfile remain retained. The default declared shell supplies the complete
tool set; no dependency guard was relaxed and no firmware rebuild was needed.

Independent finalization review also reproduced two failures using **actual
owned temporary files and flocks**, with lifecycle, runtime and hardware
boundaries explicitly modeled:

1. Unknown modeled resource closure plus failed shared-marker creation leaves
   the active lease but releases the original lock. A fresh owned lock and the
   shared pending/inherited-lock guards pass. This does not prove every device
   route admits: the USB trial's separate active-lease guard may still refuse.
2. Marker unlink followed by failed directory sync and corrective marker,
   lease and journal writes leaves an older completed-looking session with no
   shared blocker.

Both in-process production `main()` calls returned2. The enclosing probe Task
exited0 because it asserted those failures. These were not externally observed
production CLI exits, false CLI0 results, real unclosed hardware or device access.
Exact failed evidence remains immutable; [sanitized checks](checks.json) bind it.

The historical six-field intended-design case and built artifacts remain intact.
**Current whole-loading review and a distinct safety candidate remain withheld.**
No registry entry, FPGA programming, register readback or clock/transport task
is accepted by this follow-up. Another photo is not needed for this software fix.

The [existing FPGA plan](../../../openspec/changes/the-fpga-route-has-a-measured-feasibility-decision/design.md#prospective-clock-finalization-correction)
now requires owner-bound shared refusal or the exact held lock through terminal
faults. Normal results stay provisional through output, persistence, marker
closure and cancellation checks under the original clock. The final operator
FD stays held until kernel process teardown. New subprocess evidence must join
actual exit0, the original deadline, owned-group/FD and marker absence, and lock
reacquisition; a callable returning0 cannot prove that release.

## Independently reviewed software correction

Correction source `84e7b0c` is merged byte-exact at `f34d46f`. The original
operator descriptor stays held through all fallible terminal effects and is
released by final kernel teardown. Marker authority requires its retained
creation inode; matching foreign bytes cannot establish ownership. Malformed
saved JSON cannot replace the live failure record. Failed settlement retains
shared refusal or the original held operator.

Independent review rehashes 758 author files, 88 execution inputs and 42 imports,
then checks all 55 descriptor/signal sites. Its 94 clock and 10 shared host tests,
six unchanged failure-probe refusals, three separate controls and five new
whole-entry failure cases pass. Root independently rehashes all 1,635 frozen
review files and joins the three exact merged source/test bytes. Native host
fixtures and modeled hardware boundaries establish software behavior only.
Earlier failures remain retained.

Arbitrary external destruction of the original descriptor together with total
shared-storage failure remains **unsupported and unqualified**; the observer
does not claim a held lock or successful invocation in that case. Fresh root
runtime, whole-loading review and a distinct documentary candidate remain
pending. No physical task, registry entry or accepted capability changes.

After those software gates, physical work still needs the matching connected
Forgix, fresh preservation, exclusive ownership and separately qualified clock,
electrical, SPI and recovery bounds. Internal FPGA tests need no ESP wiring.

## Corrected runtime checkpoint

Fresh root preparation at `83d6a23` passes actual Task exit0 in 16.368 seconds. Independent whole saved review joins all88 inputs,42 project imports,seven tools,268 content-verified Nix paths,1,097 edges and unchanged ARM003/FPGA001 artifacts. Registration-time metadata changes are retained as a distinct environment; matching content does not imply identical runtime receipts. This remains software preparation. Current candidate binding, device preservation and physical admission remain open.
