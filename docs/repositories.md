# Repositories

All the repositories that make up the Squonk2 Job ecosystem. Each is a
submodule of this umbrella repository so everything Job-related can be
cloned from one place:

```bash
git clone --recurse-submodules git@github.com:InformaticsMatters/squonk2-jobs.git
```

By convention Job repositories carry the `squonk2-jobs` GitHub **Topic**.

## Repositories that contain Jobs

| Repository | Jobs | Notes |
| ---------- | ---- | ----- |
| [virtual-screening](https://github.com/InformaticsMatters/virtual-screening) | Virtual screening, RDKit, XChem, MolDB, DMPK, silicos-it, fragnet-search and more | The reference multi-manifest repository (several manifests in `data-manager/`). MolDB Jobs need a database deployed to the DM namespace; fragnet-search Jobs need an `im-fragnet-graph` Secret (neo4j `username`, `password`, `server`) |
| [squonk2-cdk](https://github.com/InformaticsMatters/squonk2-cdk) | Chemistry Development Kit tools | Compact single-collection exemplar (Java/Gradle) |
| [squonk2-chemaxon](https://github.com/InformaticsMatters/squonk2-chemaxon) | ChemAxon tools | May require a license via an Account Server **Asset** |
| [squonk2-fragmenstein](https://github.com/InformaticsMatters/squonk2-fragmenstein) | Fragmenstein merges | |
| [squonk2-jaqpot](https://github.com/InformaticsMatters/squonk2-jaqpot) | Jaqpot models | A good fork-and-run starter (Python, docker-compose build) |
| [squonk2-smartcyp](https://github.com/InformaticsMatters/squonk2-smartcyp) | SMARTCyp | Default branch is `master` |
| [squonk2-desc-mordred](https://github.com/InformaticsMatters/squonk2-desc-mordred) | Mordred descriptor generation | |
| [squonk2-desc-rdkit](https://github.com/InformaticsMatters/squonk2-desc-rdkit) | RDKit descriptor and fingerprint calculation | |
| [squonk2-train-test-split](https://github.com/InformaticsMatters/squonk2-train-test-split) | Dataset train/test/validation splitting | |
| [squonk2-skl](https://github.com/InformaticsMatters/squonk2-skl) | scikit-learn hyperparameter optimisation | |

The manifests currently deployed to Informatics Matters installations are
listed on the DM Wiki's
[Day 1 Jobs](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/day-1-jobs)
page.

## Repositories important for Job development

### squonk2-data-manager-job-decoder

[squonk2-data-manager-job-decoder](https://github.com/InformaticsMatters/squonk2-data-manager-job-decoder)
— PyPI: [`im-data-manager-job-decoder`](https://pypi.org/project/im-data-manager-job-decoder/)

The source of the **schemas** for Job Definition and Manifest files (see
[Job Definitions](job-definitions.md)). Distributed as a Python package
whose `decoder` module the Data Manager uses to *validate* files as they
are loaded. To keep the DM loosely coupled to the file structure, the
decoder also provides query functions: the DM asks the decoder for *what*
it wants (e.g. `decoder.get_job_doc_url()`) rather than knowing *where*
the element lives. It also renders the Jinja2 (`JINJA2_3_0`) command
templates via `decoder.decode()`.

The schema is deliberately incomplete: it covers the areas that are
considered stable; areas still being experimented with are not yet
constrained.

### squonk2-data-manager-job-utilities

[squonk2-data-manager-job-utilities](https://github.com/InformaticsMatters/squonk2-data-manager-job-utilities)
— PyPI: [`im-data-manager-job-utilities`](https://pypi.org/project/im-data-manager-job-utilities/)

A Python package Jobs can import to simplify the generation of **Event**
lines (`DmLog.emit_event()`) and **Cost** lines (`DmLog.emit_cost()`) —
see [Events and Costs](events-and-costs.md).

### squonk2-rdkit-utilities

[squonk2-rdkit-utilities](https://github.com/InformaticsMatters/squonk2-rdkit-utilities)
— PyPI: [`im-rdkit-utilities`](https://pypi.org/project/im-rdkit-utilities/)

A Python package (`rdkit_utils`) of RDKit-specific helpers — molecule
readers/writers over SDF and delimited-SMILES formats, fragment selection,
and small molecule-inspection helpers — consolidated from the copies that
had diverged across several Job repositories.

### squonk2-data-manager-job-tester

[squonk2-data-manager-job-tester](https://github.com/InformaticsMatters/squonk2-data-manager-job-tester)
— PyPI: [`im-jote`](https://pypi.org/project/im-jote/)

The **Job Tester** (`jote`) — an out-of-cluster framework for *functional*
testing of Jobs, driven by the `tests` sections of Job Definitions — see
[Testing Jobs](testing-jobs.md).

## Repositories for the Kubernetes Job operator

### squonk2-data-manager-job-operator

[squonk2-data-manager-job-operator](https://github.com/InformaticsMatters/squonk2-data-manager-job-operator)

A [kopf](https://kopf.readthedocs.io/)-based Kubernetes **Operator**, used
by the DM to manage (create and delete) the transient Job Pods. It is a
cluster-level operator that can serve more than one DM installation in a
cluster. Its versioning convention is notable: the MAJOR version tracks the
Kubernetes minor release it is built against (e.g. `33.x.x` is built with
the Python `kubernetes` 33.x client for Kubernetes 1.33).

### squonk2-data-manager-job-operator-ansible

[squonk2-data-manager-job-operator-ansible](https://github.com/InformaticsMatters/squonk2-data-manager-job-operator-ansible)

The Ansible playbooks and Kubernetes object definitions used to deploy the
Job Operator.

## Related

- [squonk2-python-cl-tools](https://github.com/InformaticsMatters/squonk2-python-cl-tools)
  — client tools, including the `load_er` exchange-rate bulk loader.
- The Data Manager itself lives in a private GitLab repository
  (`gitlab.com/informaticsmatters/squonk2-data-manager`); its public user
  documentation is on
  [GitLab Pages](https://informaticsmatters.gitlab.io/squonk2-data-manager/).
