# Local RDS decoder build and application scope

The [actual receive evidence](../../evidence/rtl-rds-trial/README.md) establishes
that the attached RTL-SDR Blog V4 can recover FM broadcast RDS at 101.1 MHz.
This application uses its tuner and continuous sample output: receive a channel,
FM-demodulate the multiplex including its 57 kHz RDS component, and validate
broadcast metadata. ESP32's sparse radio snapshots are a separate observation
mode and have not demonstrated this application or coverage of this band.

Primary sources:

- [redsea v1.3.1](https://github.com/windytan/redsea/tree/v1.3.1), commit `4cc27df9939798e800c4ff7cb484be6d9bf68b4d`: decoder, input modes and RTL-FM example.
- [liquid-dsp v1.8.3](https://github.com/jgaeddert/liquid-dsp/tree/v1.8.3), commit `10041f70cebbe3b97887e75bb41e48b73dda1b23`: local DSP runtime library.
- [redsea checkword/offset handling](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/block_sync.cc#L270) and [RBDS PI-to-callsign decoding](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/tables.cc#L271).
- [WXJC's station-owned website](https://www.wxjcradio.com/): frequency and station identity checked on 2026-10-01.

## Build without system installation

Prerequisites on this host were C/C++17 compiler, CMake, Meson, Ninja,
libsndfile 1.2.2, nlohmann-json 3.12.0, and Python with numpy/scipy/matplotlib.
Catch2 3.15.3 is needed only for upstream decoder tests. Nothing required root
or modified system libraries. From the repository root:

```sh
git clone --depth 1 --branch v1.3.1 https://github.com/windytan/redsea.git .scratch/redsea-src
git clone --depth 1 --branch v1.8.3 https://github.com/jgaeddert/liquid-dsp.git .scratch/liquid-src
cmake -S .scratch/liquid-src -B .scratch/liquid-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/.scratch/rds-prefix"
cmake --build .scratch/liquid-build -j4
cmake --install .scratch/liquid-build
CXXFLAGS="-I$PWD/.scratch/rds-prefix/include" LDFLAGS="-L$PWD/.scratch/rds-prefix/lib -Wl,-rpath,$PWD/.scratch/rds-prefix/lib" meson setup .scratch/redsea-build .scratch/redsea-src
ninja -C .scratch/redsea-build -j4
```

The trial tool uses fixed gain, no bias tee, a 1–60 second capture bound,
SIGINT and fallback termination, explicit hashes and raw decoded blocks.
Before any capture, establish receiver ownership and verify that device index
0 is the intended V4. The stored sanitized driver log confirms this trial's
device model. The tool does not lock against another operator or identify
multiple dongles itself.

```sh
python3 tools/RDS_trial.py --iq .scratch/fm101.iq --redsea .scratch/redsea-build/redsea --private-mpx .scratch/new-offline-mpx.wav --output docs/evidence/rtl-rds-trial --name retained
python3 tools/RDS_trial.py --capture-seconds 30 --redsea .scratch/redsea-build/redsea --private-mpx .scratch/new-live-mpx.pcm --output docs/evidence/rtl-rds-trial --name live
python3 tools/RDS_test.py
python3 tools/RDS_plot.py --folder docs/evidence/rtl-rds-trial
```

Choose fresh private MPX paths; the tool rejects overwriting them. Public output
files are replaced, so use a new evidence directory for a separate trial.
Upstream tests require paths relative to their source tree:

```sh
meson configure .scratch/redsea-build -Dbuild_tests=true
ninja -C .scratch/redsea-build -j4
mkdir -p .scratch/redsea-src/build
cd .scratch/redsea-src/build
../../redsea-build/redsea-test
```

The successful test includes one explicitly expected upstream RadioText corner
case failure. Program-service names can rotate or be malformed, and a valid
checkword does not make their content correct. Preserve decoder output rather
than replacing it with a guessed name. Station PI and public-source frequency
agreement provide the attribution in this trial.
