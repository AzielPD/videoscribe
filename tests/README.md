# Tests

Checks that VideoScribe starts correctly on Linux, run inside a container so
the result does not depend on whatever happens to be installed on the machine
running them.

## What is covered

Everything a user meets **before** any video is processed:

- The package imports and every module compiles.
- ffmpeg is found through the Unix search paths, not just the Windows ones.
- `doctor` reports a missing package rather than crashing on it.
- `models` prints the model table.
- The shell scripts are valid bash and have the right line endings.
- `init.sh --dry-run` and `--help` work without changing anything.
- The menu draws, accepts every option, rejects invalid input, and handles the
  input stream ending without a traceback.
- The menu with a video waiting: the model table, the download sizes, and
  declining at the confirmation prompt.
- Option 2 with no image model configured: it explains the problem and offers
  to continue with a transcript instead.

## What is not covered

No video is transcribed. That needs faster-whisper, a model download of at
least 75 MB and several minutes of CPU, which would make the suite too slow to
run often. The container deliberately leaves faster-whisper out so that the
"this package is missing" path gets exercised for real.

Verify actual processing by hand on a short sample:

```bash
python videoscribe.py run --file inbox/<something>.mp4 \
    --start 00:12:00 --duration 00:02:00 --model tiny --describe \
    --output output_test
```

## Running them

```bash
bash tests/run_container_tests.sh
```

Requires podman. For docker instead:

```bash
ENGINE=docker bash tests/run_container_tests.sh
```

The image builds in about a minute and the suite then runs in a few seconds.
`.containerignore` keeps your videos and results out of the build context;
without it the build would copy every gigabyte in `inbox/`.

## Adding a test

`check` takes five arguments and then the command to run:

```bash
check "<name>" "<what to type on stdin>" <expected exit code> "<text that must appear>" \
    <command...>
```

Use `any` for the exit code when you only care about the output. Menu input is
a plain string with newlines, one per prompt:

```bash
check "option 3 reports the machine" \
    "3
" 0 "CPU cores" \
    python videoscribe.py
```

## Two bugs these tests have already caught

**`run.cmd` had LF line endings.** Batch files with Unix line endings can break
`goto` in cmd.exe, and `run.cmd` uses labels. Fixed, and `.gitattributes` now
pins `*.cmd` to CRLF so a clone cannot reintroduce it.

**The build context included a 3 GB video.** `COPY . /app` pulled in everything
in `inbox/`. Fixed with `.containerignore`.

Both were invisible on the development machine and only showed up when the code
was moved to another platform. That is the point of running these in a
container.
