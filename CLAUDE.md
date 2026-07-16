# CLAUDE.md

Guidance for working in this repository.

## What this repository is

This is an **umbrella repository** for the Squonk2 job ecosystem. It contains no
source of its own; instead it gathers all the job-related repositories together
as git **submodules** so they can be managed independently while this repo acts
as a convenient single "root" for everything job-related.

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

### Repositories important for job development

- `squonk2-data-manager-job-decoder`
- `squonk2-data-manager-job-utilities`
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
