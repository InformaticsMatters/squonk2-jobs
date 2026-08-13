# CLAUDE.md

Guidance for working in this repository.

## What this repository is

This is an **umbrella repository** for the Squonk2 job ecosystem. It contains no
source of its own; instead it gathers all the job-related repositories together
as git **submodules** so they can be managed independently while this repo acts
as a convenient single "root" for everything job-related.

## Documentation

The `docs/` directory is the **authoritative** home for all documentation
relating to Data Manager Jobs — start at `docs/README.md`. Documentation
lives here; the other repositories (submodules) enforce or follow it and
must not duplicate it. When documentation needs correcting or extending,
change it here first.

### Job versioning

Relevant pages on the (private) Data Manager wiki — they need GitLab access
to the `squonk2-data-manager` project, so public tooling cannot read them:

- [Job Versioning](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/job-versioning)
- [Day 1 Jobs](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/day-1-jobs)
  — the manifest URLs actually deployed to Informatics Matters installations
- [Day 1 Rates](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/day-1-rates)

**Do not treat the Job Versioning wiki page as a stricter authority than
`docs/versioning.md`.** It is not: the two are near-identical, and
`docs/versioning.md` is the better-maintained rewrite. In particular the wiki
page *permits* the `latest`/`stable` scheme ("as long as you understand the
risk, that is perfectly fine").

What both documents establish:

- Two version values matter — the Job Definition's **`version`** and the
  **tag** of its container image. Changing an image means bumping the
  `version` of **every** Job Definition that uses it.
- The DM treats `latest` and `stable` as **dynamic** (always re-pulled) and
  every other tag as **static** (cached per Kubernetes node).
- Never move a Git tag, reuse a container tag, or remove a repository,
  manifest or image that is in circulation.

Stricter rules exist that **neither document states** — production Job
Definitions must not pin `latest`/`stable`; manifests should be loaded from a
repository **tag**, not a branch; the DM's `DEVELOPMENT` mode is what allows
definitions to be adjusted or removed. These come from maintainers (see
[issue #43](https://github.com/InformaticsMatters/squonk2-jobs/issues/43)) and
are the subject of that issue. Until they are written down, **ask a maintainer
rather than inferring policy from either the docs or the repositories** — the
repositories largely follow the permissive documented scheme, which is how the
divergence arose.

## Layout

Each submodule is a separate, independently managed repository. They fall into
three groups:

### Repositories that contain Jobs

- `virtual-screening`
- `squonk2-cdk`
- `squonk2-chemaxon`
- `squonk2-fragmenstein`
- `squonk2-jaqpot`
- `squonk2-smartcyp`
- `squonk2-desc-mordred`
- `squonk2-desc-rdkit`
- `squonk2-train-test-split`
- `squonk2-skl`

### Repositories important for job development

- `squonk2-data-manager-job-decoder`
- `squonk2-data-manager-job-utilities`
- `squonk2-rdkit-utilities`
- `squonk2-data-manager-job-tester`

### Repositories for the Kubernetes Job operator

- `squonk2-data-manager-job-operator`
- `squonk2-data-manager-job-operator-ansible`

## Working with the submodules

Clone with submodules:

```bash
git clone --recurse-submodules git@github.com:InformaticsMatters/squonk2-jobs.git
```

If you already cloned without them:

```bash
git submodule update --init --recursive
```

Pull the latest for every submodule:

```bash
git submodule update --remote --merge
```

Each submodule is pinned to a specific commit in this repository. To advance a
submodule, make and push changes **inside** that submodule's own repository,
then commit the updated submodule pointer here.

## Conventions

- Make changes to job code inside the relevant submodule, not here — this repo
  only tracks which commit of each submodule is current.
- Never commit directly to `main` (or any default branch); open a pull request.
- Before running `jote` against a Nextflow-type Job, match your local
  `nextflow` version to the one pinned in that submodule's
  `Dockerfile-nextflow` — see [Matching the Nextflow version](docs/testing-jobs.md#matching-the-nextflow-version).
  Using the wrong version produces failures that look like broken workflows
  but are actually just version skew.
