# Initialization diagnostic, 2026-10-01

**Physical result:** the diagnostic build reaches `command-loop-ready` and
answers INFO, SYNC, BAUD?, CAPS and LIMITS? correctly at 115,200 baud.
This rules out an initialization stall for this build. It does not establish
capture reliability or RF reception, and the instrumented image is not the RF
baseline.

Root installed the [pinned diagnostic image](../firmware-diagnostic/README.md)
with `tools/flash_trial.py install`; [write.log](write.log) records successful
esptool verification. [manifest.json](manifest.json) identifies every written
part. The [fresh boot](boot-inspection/boot.log) identifies `550fade-diag115k`
and records each completed Wi-Fi and ROM initialization step. UART marker
printing loses part of one line around transport configuration, but the final
ready marker and actual command replies are present.

The probe opened the selected CP2102 port exclusively at 115,200, waited 1.5 s,
then issued INFO, SYNC 12345, BAUD?, CAPS and LIMITS? in order. Exact responses
are in [protocol.json](protocol.json). The handle was closed afterward.
No IQ or spectrum was acquired in this diagnostic test.

The [upstream 2 Mbaud trial](../sdr-installation/README.md) and
[1 Mbaud trial](../sdr-installation-uart1m/README.md) booted but returned no
protocol responses. Silicon Labs documents default classic CP2102 rates
through 921,600 and custom baud configuration separately in
[the CP2102/9 data sheet](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf).
That supports testing a clean 921,600-baud image; the present result alone
does not measure the physical baud of either failed trial.
