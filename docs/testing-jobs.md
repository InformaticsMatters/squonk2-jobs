# Testing Jobs with `jote`

> This is the authoritative guide to Job testing. The Job Tester's own
> repository is
> [squonk2-data-manager-job-tester](https://github.com/InformaticsMatters/squonk2-data-manager-job-tester);
> the test-block grammar it consumes is enforced by the schema in the
> [squonk2-data-manager-job-decoder](https://github.com/InformaticsMatters/squonk2-data-manager-job-decoder)
> repository.

The **Squonk2 Job Tester** (`jote`) is a Python utility that runs the tests
defined in a Job repository's Job Definitions against the Job's container
image — an image typically built from the same repository.

`jote` runs Job implementations in a file-system environment that replicates
what they find when run by the Data Manager. Jobs are **not**, however,
running in the same operating-system environment — they are not bound by the
processor and memory constraints they will encounter in the Data Manager,
which runs them in [Kubernetes](https://kubernetes.io/).

A successful test should give you confidence that a Job *should* work in the
Data Manager, but without writing a good set of tests you will never be
completely confident that it always will. `jote` exists to provide
confidence that Jobs are basically fit for purpose before deployment —
**Jobs that have no tests will not normally be deployed to a Data Manager.**

## Installation

`jote` is published on [PyPI](https://pypi.org/project/im-jote/):

```bash
pip install im-jote
```

It is a Python 3 utility (ideally use Python 3.10 or later). You will also
need [Docker](https://docs.docker.com/get-docker/) and `docker-compose`
(v1 or v2), and — only if you test nextflow Jobs —
[nextflow](https://www.nextflow.io/).

## Repository expectations

To test (and use) Jobs, the repository needs at least one
**[Manifest](job-definitions.md#the-manifest-file)** and one
**[Job Definition](job-definitions.md#the-job-definition-file)** file in its
`data-manager` directory. `jote` expects the default manifest to be called
`manifest.yaml`, but you can use a different name (`--manifest`) and have
more than one.

As well as executing tests, `jote` checks that the repository structure is
as expected, validates the YAML files against the official schemas, and
applies strict formatting rules to them.

## Writing tests

Tests are named blocks in the `tests` section of a Job's definition. Each
test can define `inputs` (files, relative to the repository root), `options`
(values for the command template), and `checks` (the pass criteria):

```yaml
jobs:
  max-min-picker:
    # ...
    tests:
      simple-execution:
        inputs:
          inputFile: data/100000.smi
        options:
          outputFile: diverse.smi
          count: 100
        checks:
          exitCode: 0
          outputs:
          - name: diverse.smi
            checks:
            - exists: true
            - lineCount: 100
```

Here the container must exit with code `0`, and the file `diverse.smi` must
exist in the generated test directory and contain 100 lines. `jote` fails
the test unless every check is satisfied.

Available output checks are `exists` and `lineCount`.

## Running tests

Run `jote` from the root of a clone of the Job repository you want to test:

```bash
jote
```

Display all options with:

```bash
jote --help
```

Useful options include `--manifest <file>` to select a manifest,
`--test <name>` to run a single named test, `--dry-run` to validate without
executing (handy in CI — see below), and `--allow-no-tests`.

### The jote container network

Tests are executed on the Docker network `data-manager_jote`, defined in the
docker-compose file `jote` generates to run your tests.

## Built-in variables

Job-definition command expansion (provided by the Job Decoder) relies on a
number of *built-in* variables. Some are provided by the Data Manager when
the Job runs under its control; `jote` provides them (and one extra) to
simplify testing:

- `DM_INSTANCE_DIRECTORY` — the path of the (simulated) instance directory,
  normally created by the Data Manager.
- `CODE_DIRECTORY` (jote only) — the root of the repository the tests run
  in. Convenient for locating an out-of-container nextflow workflow file,
  which is likely to be in the root of your repository.

## Ignoring tests

You may want to disable tests that need more work before they are complete.
Mark individual tests with an `ignore` declaration:

```yaml
tests:
  simple-execution:
    ignore:
    # ...
```

You do not have to remove `ignore` to run the test: naming a test explicitly
with `--test` runs it regardless of its `ignore` state.

## Test run levels

Tests can be assigned a `run-level` — a numeric value (1..100) used to group
tests, typically by execution time (short tests low, long tests high):

```yaml
tests:
  simple-execution:
    run-level: 5
    # ...
```

By default `jote` executes tests that have no run-level and those with
run-level `1`. Passing `--run-level N` runs all tests up to *and including*
level `N` (plus those without any run-level).

## Test timeouts

`jote` lets each test run for 10 minutes before cancelling (and failing) it.
If a test needs longer, set `timeout-minutes`:

```yaml
tests:
  simple-execution:
    timeout-minutes: 120
    # ...
```

Avoid creating too many long-running tests; if you cannot, consider using
`run-level` so they are not run by default.

## Test groups

Normally the test environment is torn down between tests. If tests depend on
the results of a prior test, run them as a **group**, which preserves the
project directory between them.

Define a `test-groups` block at the root of the Job Definition file:

```yaml
test-groups:
- name: experiment-a
```

then place tests in the group with a `run-groups` declaration:

```yaml
jobs:
  max-min-picker:
    # ...
    tests:
      test-a:
        run-groups:
        - name: experiment-a
          ordinal: 1
```

The `ordinal` (1..N, unique within the group) fixes each test's position in
the group's execution sequence — a test with ordinal `1` runs before a test
with ordinal `2`.

Run the tests of a specific group with:

```bash
jote --run-group experiment-a
```

### Running additional containers (group testing)

Test groups can launch additional support containers — for example a
background database used by the group's tests. Provide a `docker-compose`
file in the `data-manager` directory and name it in the `test-groups`
declaration:

```yaml
test-groups:
- name: experiment-a
  compose:
    file: docker-compose-experiment-a.yaml
    delay-seconds: 10
```

The compose filename must begin `docker-compose` and end `.yaml`. The
compose file is started before the first test in the group runs and stopped
after the last. It is run *detached* — `jote` does not wait for the
containers to initialise — so use `delay-seconds` to insert a fixed delay
between starting the compose file and running the first test, reducing the
risk that your containers are not ready.

## Nextflow test execution

Job image types can be `simple` or `nextflow` (the `image.type` field —
see [Job Definitions](job-definitions.md#the-image-block)). Simple Jobs are
executed in the container image you built and behave much as they do in the
Data Manager. Nextflow Jobs are executed using the shell, relying on Docker
as the execution run-time for the workflow's processes.

Be aware that nextflow tests run by `jote` run under different conditions
than under the Data Manager, where nextflow executes within Kubernetes.
Under `jote` the nextflow controller runs in the shell and is not subject to
the same memory or processor constraints — a variability you need to take
into account.

You may need a custom nextflow configuration for tests to run successfully.
Add a `nextflow-config-file` declaration to the test:

```yaml
tests:
  simple-load:
    nextflow-config-file: nextflow-test.config
    # ...
```

The config file must be located in the repository's `data-manager`
directory. Before running the test, `jote` copies it to the Job's project
directory as `nextflow.config` (the standard file nextflow expects).

`jote` **will not** let you run with a nextflow config in your home
directory, as any settings found there would be merged with the file `jote`
writes, potentially disturbing execution behaviour.

> It is your responsibility to install a suitable nextflow available for
> shell execution — `jote` expects to be able to run `nextflow` when
> executing the corresponding `command` in the Job Definition.

## Running jote in CI

Run `jote --dry-run` in CI to validate manifests, definitions and repository
structure on every change without executing containers. The
[virtual-screening test workflow](https://github.com/InformaticsMatters/virtual-screening/blob/main/.github/workflows/test.yaml)
is a good example — it runs `jote --manifest <name> --dry-run` for every
manifest in the repository.
