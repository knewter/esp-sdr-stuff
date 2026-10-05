# Timed source003 startup refinement (prospective)

The preserved source002 host preparation uses the reviewed CID startup helper.
Independent receiver-helper testing found that entering the deferred-cancellation
context can consume the remaining original startup budget before `Popen`.
Source003 will be a separate private replacement with a fresh check of the same
original bound inside that context immediately before the actual spawn.

Tests will reject both late and exact-deadline context entry without launching,
retain and close an actual harmless child for the valid entry case, and exercise
cancellation in an isolated owned process so startup ownership survives deferred
signal delivery. The old 96 groups, source002, original failed physical source
attempt and historical read-only benchmark remain preserved. No automatic retry
or speculative profile fallback is introduced.

The source165/45, monitor75/80, caller30, native32 and outer300 limits are unchanged,
as are the typed timer profile, wire/ACK, full NAR/archive/image/controller and
inherited-lock gates. A current full root admission and timing review, independent
host review and actual source-only qualification are still required. This host
refinement does not qualify RF, count air emissions or check physical task4.3.
Root remains the sole device, daemon, archive and hardware operator.
