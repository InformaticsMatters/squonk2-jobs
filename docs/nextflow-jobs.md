# Nextflow Jobs — authoring guide

Most Jobs are `simple`: the Data Manager (DM) runs a single command in a single
container. A **Nextflow Job** is different — its command starts a
[Nextflow](https://www.nextflow.io/) workflow, and Nextflow orchestrates the
real work as a graph of **processes**, each of which can run in its own
container image.

This guide covers how to author a Nextflow Job. For the general reference to
Job Definitions see [Job Definitions](job-definitions.md); for running the
tests see [Testing Jobs](testing-jobs.md#nextflow-test-execution). The
worked examples below are taken from the
[`virtual-screening`](https://github.com/InformaticsMatters/virtual-screening)
repository.

## When to use Nextflow

Reach for a Nextflow Job when the task is naturally a **pipeline** rather than a
single step — for example: split a large input into chunks, run an expensive
per-chunk computation in parallel, then collect the results. Nextflow gives you
chunking, parallelism, retries and resource management for free, and lets each
step run in the container image best suited to it.

If your Job is a single tool invocation, keep it `simple` — the extra moving
parts of Nextflow are not worth it.

## The two-container model

This is the key idea that trips people up: a Nextflow Job involves **two kinds
of image**.

1. **The controller image** — a small image that contains only Nextflow (the
   Java runtime plus the `nextflow` binary) and your workflow files (`*.nf`).
   This is the image named in the Job Definition's `image.name`. It runs the
   `nextflow run …` command but does *no* scientific work itself. In
   `virtual-screening` this is `informaticsmatters/vs-nextflow`, built from
   [`Dockerfile-nextflow`](https://github.com/InformaticsMatters/virtual-screening/blob/main/Dockerfile-nextflow).

2. **The process images** — the images that actually do the work. Each Nextflow
   `process` declares the image it needs with a `container` directive, and
   Nextflow pulls and runs it. These are your normal per-tool images (e.g.
   `informaticsmatters/vs-rdock`, `informaticsmatters/vs-plants`).

So the DM launches the controller; the controller launches everything else.

```
Data Manager
  └─ controller pod  (image: vs-nextflow, type: nextflow)
       └─ nextflow run workflow.nf
            ├─ process A  → container: vs-rdkit
            ├─ process B  → container: vs-plants
            └─ …          (fanned out / parallelised by nextflow)
```

## The Job Definition

Mark the Job as Nextflow with `type: nextflow` in the [`image`
block](job-definitions.md#the-image-block), and make the `command` a
`nextflow run` invocation. Everything else — `variables`, `inputs`, `outputs`,
`options`, `tests` — is exactly as for a simple Job.

```yaml
run-rdock:
  name: Run rDock docking
  version: '1.0.0'
  category: virtual screening
  keywords:
  - rdock
  - docking
  - nextflow
  image:
    name: informaticsmatters/vs-nextflow   # the controller image
    tag: 'stable'
    project-directory: /data
    working-directory: /data
    type: nextflow                          # <-- makes this a Nextflow Job
    memory: 1Gi
    cores: 250m
    fix-permissions: true
  command: >-
    nextflow -log {{ DM_INSTANCE_DIRECTORY }}/nextflow.log
    run {{ CODE_DIRECTORY|default('/code') }}/rdock-docking.nf
    --ligands '{{ ligandsSDF }}'
    --protein '{{ proteinMOL2 }}'
    --prmfile '{{ prmFile }}'
    --asfile '{{ asFile }}'
    --num_dockings {{ numDockings }}
    --output_basename {{ outputFile }}
    --mode {{ mode }}
    {% if resultsDir is defined %}--publish_dir {{ resultsDir }}{% endif %}
    -with-trace {{ DM_INSTANCE_DIRECTORY }}/trace.txt
    -with-report {{ DM_INSTANCE_DIRECTORY }}/report.html
```

### Anatomy of the command

The command is [Jinja2-expanded](job-definitions.md) by the Job Decoder before
it runs. A few conventions are worth calling out:

| Fragment | Why |
| -------- | --- |
| `nextflow -log {{ DM_INSTANCE_DIRECTORY }}/nextflow.log` | Writes the Nextflow controller log into the **instance directory** so it survives with the Job's other artifacts |
| `run {{ CODE_DIRECTORY\|default('/code') }}/rdock-docking.nf` | Locates the workflow file. Under the DM it is baked into the image at `/code`; under `jote` the built-in `CODE_DIRECTORY` points at your checkout so you can run the workflow without rebuilding the image (see [below](#where-the-workflow-files-live)) |
| `--ligands '{{ ligandsSDF }}'` | Nextflow `params.*` are set with `--<name>` flags. Quote file paths — filenames may contain spaces |
| `{% if resultsDir is defined %}--publish_dir {{ resultsDir }}{% endif %}` | Only pass optional flags when the option was supplied |
| `-with-trace …/trace.txt` and `-with-report …/report.html` | Ask Nextflow to write its execution trace and HTML report into the instance directory — invaluable when a run misbehaves |

> **Match `outputs.creates` to `--publish_dir`.** Nextflow only makes a
> process's output available outside its work directory when the workflow
> `publish`es it. Ensure the path your workflow publishes to matches the
> `creates:` expression in the Job's `outputs`, e.g.
> `creates: '{% if resultsDir is defined %}{{ resultsDir }}/{% endif %}{{ outputFile }}.sdf'`.

## Where the workflow files live

Workflow files (`*.nf`) are **copied into the controller image** at build time.
In `virtual-screening` the [`Dockerfile-nextflow`](https://github.com/InformaticsMatters/virtual-screening/blob/main/Dockerfile-nextflow)
does:

```dockerfile
ENV HOME=/code
WORKDIR ${HOME}
COPY *.nf ./
COPY nf-processes ./nf-processes
```

That is why the DM command references `/code/rdock-docking.nf`. When testing
with `jote`, the built-in `CODE_DIRECTORY` variable points at your working copy
instead, so `{{ CODE_DIRECTORY|default('/code') }}` runs the *checked-out*
workflow — edit a `.nf` file and re-run the test without rebuilding the image.

A workflow is typically split into a top-level file that wires processes
together and a library of reusable processes under `nf-processes/`:

```groovy
// rdock-docking.nf (top-level workflow)
nextflow.enable.dsl=2

params.inputs = 'need-conf.smi'
params.chunk_size = 10000

include { split_txt }     from './nf-processes/file/split_txt.nf' addParams(suffix: '.smi')
include { gen_conformers } from './nf-processes/rdkit/gen_conformers.nf'

workflow {
    split_txt(file(params.inputs))
    gen_conformers(split_txt.out.flatten())
}
```

## Processes and their containers

Each process names the image it runs in with a `container` directive. Nextflow
pulls that image and runs the process's script inside it:

```groovy
process pharmacophore {

    container 'informaticsmatters/vs-plants:stable'

    input:
    path inputs
    path fragments

    output:
    path "ph4_${inputs.name}", optional: true

    """
    /code/pharmacophore.py --input '$inputs' --fragments '$fragments' …
    """
}
```

Because the *process* images carry the science, the controller image stays
small and rarely changes. Pin process containers to `stable` (or a fixed tag)
for reproducibility — see [Versioning](versioning.md).

## nextflow.config

Nextflow reads a `nextflow.config` from the working directory. The important
settings for DM Jobs enable Docker as the process executor and make containers
run as an arbitrary uid/gid (the DM does not know in advance which user the
Project will run as):

```groovy
docker {
    enabled = true
    runOptions = '-u $(id -u):$(id -g) --network=host'
    envWhitelist = 'POSTGRES_SERVER,POSTGRES_DATABASE,POSTGRES_USERNAME,POSTGRES_PASSWORD'
}
process.container = 'centos:7'   // fallback for processes with no container directive
```

- **`enabled = true`** — run each process in its declared `container`.
- **`runOptions` uid/gid** — required so output files are owned correctly and
  the DM can manage them afterwards (pair this with `fix-permissions: true` in
  the image block).
- **`envWhitelist`** — only listed environment variables are forwarded into
  process containers; add any your processes need (e.g. database credentials
  injected via the Job Definition's `environment`).

> Under the DM, Nextflow runs inside Kubernetes with the memory and CPU limits
> from the image block. Under `jote` it runs in your shell with **no** such
> limits — see the caveats in
> [Testing Jobs](testing-jobs.md#nextflow-test-execution).

## Instance-directory artifacts

Directing Nextflow's log, trace and report into `{{ DM_INSTANCE_DIRECTORY }}`
means they land alongside the Job's outputs and are available for download and
debugging after the run:

| File | Produced by | Contents |
| ---- | ----------- | -------- |
| `nextflow.log` | `-log` | Controller log (scheduling, retries, errors) |
| `trace.txt` | `-with-trace` | Per-process timing, exit codes, resource use |
| `report.html` | `-with-report` | Human-readable execution report |

## Events, costs and logs

Nextflow Jobs emit [Events and Costs](events-and-costs.md) the same way simple
Jobs do — as specially formatted stdout lines. Note that because a Nextflow run
interleaves the controller's and the processes' output, the DM's **KEW** parses
`nextflow` Job logs with a different function from `simple` Jobs (see
[Architecture](architecture.md#kew--the-kubernetes-event-watcher)). Emit your
`-EVENT-` / `-COST-` lines from the process scripts where the work actually
happens.

## Testing

Test Nextflow Jobs with `jote` exactly as you would any other Job, but be aware
of the execution differences and the `nextflow-config-file` test declaration —
these are documented in
[Testing Jobs → Nextflow test execution](testing-jobs.md#nextflow-test-execution).
In short:

- You must have a `nextflow` binary on your `PATH`; `jote` shells out to it.
- Provide a `nextflow-config-file` in your `data-manager` directory if the
  test needs config that differs from production; `jote` copies it to
  `nextflow.config` before the run.
- `jote` refuses to run if a `nextflow.config` exists in your home directory.

## Checklist for a new Nextflow Job

- [ ] Workflow (`*.nf`) written and copied into the controller image.
- [ ] Each `process` declares a `container`.
- [ ] `nextflow.config` enables Docker and runs as the invoking uid/gid.
- [ ] Job Definition sets `image.type: nextflow` and `fix-permissions: true`.
- [ ] `command` uses `-log`, `-with-trace`, `-with-report` into
      `DM_INSTANCE_DIRECTORY`, and `CODE_DIRECTORY|default('/code')` for the
      workflow path.
- [ ] `outputs.creates` matches the workflow's `--publish_dir` location.
- [ ] Tests pass under `jote`, with a `nextflow-config-file` if needed.
