# Getting Started — writing your first Job

This tutorial takes you from a working command-line tool to a Job that can be
loaded into a Squonk2 Data Manager. It assumes you are comfortable with Git,
Docker, and (typically) Python.

A **Job** is, at heart, a program packaged in a container image, described by
a **Job Definition** (YAML), and published through a **Job Manifest** (YAML).
The Data Manager runs the container as a Kubernetes Pod with the user's
**Project** directory mounted so the Job can read and write the user's files.

If you prefer to learn from working examples, the
[squonk2-cdk](https://github.com/InformaticsMatters/squonk2-cdk) repository is
a compact single-collection example, and
[virtual-screening](https://github.com/InformaticsMatters/virtual-screening)
is the reference multi-manifest repository.
[squonk2-jaqpot](https://github.com/InformaticsMatters/squonk2-jaqpot) is a
good fork-and-run starter.

## 1. Write the tool

Your tool is an ordinary command-line program. Conventions that make a good
Job:

- **Parameterise everything** through command-line arguments (for Python,
  `argparse`). The Job Definition maps user-supplied values onto these
  arguments.
- **Read and write files relative to the working directory.** The Data
  Manager mounts the user's Project directory into the container and runs
  your command there.
- **Log to stdout.** The Data Manager collects the container's stdout; this
  is how [Events and Costs](events-and-costs.md) reach the user and the
  Account Server. For Python, the
  [`im-data-manager-job-utilities`](https://pypi.org/project/im-data-manager-job-utilities/)
  package provides `DmLog.emit_event()` and `DmLog.emit_cost()`.
- **Create output files with sensible permissions.** Files a Job creates must
  be readable by the Data Manager once the Job completes. The simplest
  approach is to set `fix-permissions: true` in the Job Definition's `image`
  block (see below), which asks the DM to fix output-file permissions after
  the Job completes successfully; alternatively `chmod 664` files as you
  create them.

A minimal Python example:

```python
#!/usr/bin/env python
import argparse
from dm_job_utilities.dm_log import DmLog

def main():
    parser = argparse.ArgumentParser(description="Count molecules")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    DmLog.emit_event("Counting molecules in", args.input)
    count = 0
    with open(args.input, encoding="utf-8") as in_file, \
            open(args.output, "w", encoding="utf-8") as out_file:
        for line in in_file:
            count += 1
            out_file.write(line)
    DmLog.emit_event("Counted", count, "molecules")
    DmLog.emit_cost(count)

if __name__ == "__main__":
    main()
```

## 2. Containerise it

Jobs are distributed as container images, normally built from the same
repository as the tool and published to a public registry (ours go to Docker
Hub as `informaticsmatters/<repository-name>`).

- The image must contain everything the tool needs — the DM does not install
  anything into it.
- Do not rely on a specific user id; the DM runs the container with the
  project directory mounted and a working directory set from the Job
  Definition.
- Build and publish images with CI. Our repositories typically publish
  `:latest` from a `staging` branch and `:stable` from `main`, plus
  immutable version tags for releases — see [Versioning](versioning.md).

Test it locally, mounting a scratch directory the way the DM will mount the
project:

```bash
docker build -t acme/mol-counter:latest .
docker run --rm -v $PWD/test-data:/data -w /data acme/mol-counter:latest \
    mol_counter.py --input mols.smi --output out.smi
```

## 3. Create the `data-manager` directory

Job Definitions and Manifests live in a `data-manager` directory at the root
of your repository:

```
your-repo/
├── data-manager/
│   ├── manifest.yaml         # the Job Manifest
│   ├── mol-tools.yaml        # a Job Definition file (one or more)
│   └── docs/
│       └── comp chem/
│           └── mol-counter.md   # per-Job user documentation
├── Dockerfile
└── ...
```

A minimal **manifest** (`data-manager/manifest.yaml`):

```yaml
---
kind: DataManagerManifest
kind-version: '2021.1'

job-definition-files:
- mol-tools.yaml
```

A minimal **Job Definition** (`data-manager/mol-tools.yaml`):

```yaml
---
kind: DataManagerJobDefinition
kind-version: '2021.1'
collection: acme-mol-tools

jobs:
  mol-counter:
    name: Molecule counter
    description: >-
      Counts the molecules in a SMILES file.
    version: '1.0.0'
    category: comp chem
    keywords:
    - demo
    image:
      name: acme/mol-counter
      tag: '1.0.0'
      project-directory: /data
      working-directory: /data
      fix-permissions: true
    command: >-
      mol_counter.py --input '{{ inputFile }}' --output '{{ outputFile }}'
    variables:
      inputs:
        type: object
        required:
        - inputFile
        properties:
          inputFile:
            title: Input molecules
            mime-types:
            - squonk/x-smiles
            type: file
      outputs:
        type: object
        properties:
          outputFile:
            title: Output molecules
            mime-types:
            - squonk/x-smiles
            creates: '{{ outputFile }}'
            type: file
      options:
        type: object
        required:
        - outputFile
        properties:
          outputFile:
            title: Output file name
            type: string
            default: counted.smi
            pattern: "^[A-Za-z0-9_/\\.\\-]+$"
```

Every element is explained in the [Job Definitions reference](job-definitions.md).
Note the `command` is a **Jinja2 template** — always wrap substituted values
in single quotes to guard against injection.

## 4. Add tests

Jobs **must** have tests — Jobs without tests will not normally be deployed
to a Data Manager. Tests live in a `tests` block inside each Job's
definition and are run by `jote`, the Job Tester:

```yaml
jobs:
  mol-counter:
    # ...
    tests:
      simple-execution:
        inputs:
          inputFile: data/mols.smi
        options:
          outputFile: counted.smi
        checks:
          exitCode: 0
          outputs:
          - name: counted.smi
            checks:
            - exists: true
            - lineCount: 100
```

Test input files (here `data/mols.smi`) live in the repository, relative to
the repository root. Install and run the tester from the repository root:

```bash
pip install im-jote
jote
```

`jote` validates your YAML against the official schemas, applies repository
sanity checks, and executes the tests in Docker — mimicking the way the
Data Manager runs the Job. See [Testing Jobs](testing-jobs.md) for the full
guide, including run levels, test groups, and sidecar containers.

## 5. Version and release

When your Job works, protect it: pin the container image to an immutable tag
and set the Job's `version`. Whenever the image content changes, publish a
new tag and bump the version of **every** Job that uses the image. The rules
(and a lighter-weight `latest`/`stable` strategy for development) are in
[Versioning](versioning.md).

## 6. Deploy it

Commit and push. Add the `squonk2-jobs` **Topic** to your repository so it can
be identified as a Job repository. Then give the *raw* URL of your manifest to
a Data Manager administrator, who loads it via the DM's
`/admin/job-manifest` API — for the example above, something like:

```
https://raw.githubusercontent.com/acme/your-repo/main/data-manager/manifest.yaml
```

See [Deploying Jobs](deploying-jobs.md), which also covers private
repositories and how administrators attach **Exchange Rates** so your Job's
reported costs are charged as coins.

## Where next?

- [Job Definitions reference](job-definitions.md) — everything the YAML can express
- [Testing Jobs](testing-jobs.md) — the full `jote` guide
- [Events and Costs](events-and-costs.md) — reporting progress and usage
- [Architecture](architecture.md) — what happens inside the DM when your Job runs
