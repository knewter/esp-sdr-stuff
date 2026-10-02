# Independent trial 001 failure review

On 2026-10-02, the offline audit passed for the retained **failed** episode at lifecycle revision `6e7b6bc617d855f38d0d62344ae939b8721c1cfe`. The five saved files bind the selected private factory identity, frozen execution sources, historical RAM artifact and immutable image. Two prior 2 MiB original copies still match their preservation hash; this does not establish the device's current flash contents.

The trace records a timeout (errno 110) during factory serial open/DTR control. The outer worker timed out; the hardware session lasted 15.732611 seconds. Parent lifecycle records owned process-group closure. This audit checks that saved attestation, without independently inspecting live PIDs or containers. No ROM/RAM load, HELLO/STATUS response, capture, fresh full-flash preservation or factory recovery is recorded. CRC, payload, END, loss and throughput results are unavailable. No acceptance claim follows from this episode.

[receipt.json](receipt.json) contains sanitized results. Replay reads saved files and Nix-store artifacts only; it opens no device and invokes no Docker:

```sh
nix develop --command task -t docs/evidence/forgix-usb-ram-trial-001-review/Taskfile.yml audit SESSION=/absolute/private/session/directory
```

Any later explicit recovery requires a separate supplement; this review retains the initial failure.
