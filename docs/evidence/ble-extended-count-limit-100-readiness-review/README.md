# Independent source-only readiness review

The separately frozen extended100 readiness caller passed offline review on 2026-10-02. [receipt.json](receipt.json) binds the exact caller, Task, tests, protocol and 22-input proof. The final locked Nix/Task replay passed 24 tests; four independent deadline/metadata probes and all 22 input bindings passed. Fixtures use synthetic count100/timing fields and establish no new physical result.

The sole source profile remains handle 1, extended properties 0, map 1, LE1M primary/secondary, 20 ms interval, the existing exact 16-byte owned AD, Duration 5,000 ms, MaxEvents 100 and one-second delay. Success still requires actual typed `0x43/count100`, source exit 0, five matching accepted command pairs, complete monitor receipt and verified owned cleanup. A typed duration diagnostic remains exit 2; cancellation or unknown closure cannot qualify.

Review found that identity/hash work after readiness could outlast the outer deadline. The replacement freeze anchors 15 seconds before monitor launch and checks the same deadline on readiness return and immediately before source launch. Independent simulated time advancing to 16 seconds after readiness now permits only the monitor to start and records failure with verified synthetic cleanup. Monitor readiness/capture/grace remain 10/30/5 seconds with a 45-second active bound; parent active supervision remains 60 seconds. Final cleanup has its existing separate finite waits.

At the offline checkpoint, runtime image and recursive closure preflight remained pending for the sole hardware operator. This review opened no device and invoked no Docker. That offline review alone provides no physical controller-limit result or RF denominator. The earlier failed caller and episode remain unchanged. The initial replay raced an author edit and failed a transient fixture; only the replacement frozen 24-test replay qualifies here.


## Actual readiness condition 001 — October 3

The sole operator ran the unchanged, separately declared source-only profile from `213aff2dede63bcc97993694fb78e11aeeea85bd` after fresh locked-image/recursive-Nix-closure review. Terminal Task exit 0: **controller_limit_verified**. Source and monitor independently parsed actual typed `0x43/count100`; 23 source records, 11 monitor records and five matching accepted command pairs passed. Monitor completed normally, source exited 0, owned source cleanup and child-group closure passed; controller state returned to powered with zero active instances.

Readiness took 3.622 s. Source child launch was 8.079 s after parent start, 6.921 s before the fixed 15 s cutoff. Monitor readiness/capture/grace stayed 10/30/5 s; parent active supervision took 40.271 s within 60 s. Enable acknowledgement to termination took 2.426 s. All 22 frozen inputs remained unchanged. Saved receipts plus reviewed cleanup code support closure; no saved exact process/container identity supports an independent historical resource query. Accepted disable/remove commands do not independently prove RF silence.

This passes one extended-advertising controller-count condition. Auxiliary-channel AD and two readers of the same controller supply no independently measured air denominator, legacy channel-37 count, reception hit rate, new ESP waveform or Trial B release. Legacy count0/unknown results and the earlier failed extended100 lifecycle remain retained. Original event-observation tasks stay open.

Private raw records remain ignored. SHA-256 bindings: lifecycle `c745df5b08c7020fb164503b482bbce52dacaf8cd476b9c73f698b7d32bf08c7`; monitor `1bdd72d09a0c139de54191966f5a1fd7e7d55890318a0b28d8c90c1709be9118`; independent actual review `dfa9289e5c7bb47f18fb467e2e60f2e6b1b90bd3c6d57334f6c607373f58401b`. The offline reviewer checked records, timing, input bindings and runtime images without hardware or Docker access.
