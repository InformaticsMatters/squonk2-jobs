# Job Definitions and Manifests — reference

Job **Manifests** and **Job Definitions** are YAML files placed in the
`data-manager` directory of a Job repository. Their structure is formally
defined by JSON schemas in the
[squonk2-data-manager-job-decoder](https://github.com/InformaticsMatters/squonk2-data-manager-job-decoder)
repository — the schemas are the authority; this document is the guide:

- [`decoder/manifest-schema.yaml`](https://github.com/InformaticsMatters/squonk2-data-manager-job-decoder/blob/main/decoder/manifest-schema.yaml)
- [`decoder/job-definition-schema.yaml`](https://github.com/InformaticsMatters/squonk2-data-manager-job-decoder/blob/main/decoder/job-definition-schema.yaml)

The Data Manager validates files against these schemas as they are loaded,
using the decoder's `validate_manifest_schema()` and `validate_job_schema()`
functions. The schema deliberately covers only the areas of the file
structure that are considered stable ("locked down"); areas still being
experimented with are not yet constrained.

> **Editor tip:** add a `yaml-language-server` comment to the top of your
> definition files to get live schema validation in editors that support it:
>
> ```yaml
> # yaml-language-server: $schema=https://raw.githubusercontent.com/InformaticsMatters/squonk2-data-manager-job-decoder/main/decoder/job-definition-schema.yaml
> ```
>
> (Pin the URL to a decoder release tag rather than `main` for stability.)

## The Manifest file

The manifest is an index: it lists the Job Definition files that form a
*package* (an inseparable unit) of related Jobs. A repository can contain
more than one manifest, each with its own list of definition files. The
default name is `manifest.yaml`, but any name can be used — the manifest's
URL is what an administrator loads.

```yaml
---
kind: DataManagerManifest
kind-version: '2021.1'

job-definition-files:
- virtual-screening.yaml
- rdkit.yaml
```

| Field | Required | Notes |
| ----- | -------- | ----- |
| `kind` | yes | Always `DataManagerManifest` |
| `kind-version` | yes | Currently `'2021.1'` |
| `description` | no | Free text |
| `job-definition-files` | yes | At least one `.yaml`/`.yml` filename, relative to the `data-manager` directory |

## The Job Definition file

A Job Definition file describes a **Collection** of one or more related Jobs.
A single file can define multiple Jobs; how Jobs are grouped into files is
the repository owner's choice.

```yaml
---
kind: DataManagerJobDefinition
kind-version: '2021.1'
name: CDK jobs
collection: cdk

jobs:
  cdk-molecular-descriptors:
    name: CDK molecular properties
    description: >-
      Calculate molecular properties using CDK's molecular descriptors.
    version: '1.0.0'
    category: comp chem
    keywords:
    - cdk
    - properties
    image:
      name: informaticsmatters/squonk2-cdk
      tag: 'latest'
      project-directory: /data
      working-directory: /data
      fix-permissions: true
    command: >-
      java squonk.jobs.cdk.DescriptorsExec
      --input '{{ inputFile }}'
      --output '{{ outputFile }}'
      {% if alogp %}--alogp{% endif %}
    # variables: and tests: follow - see below
```

Top-level fields:

| Field | Required | Notes |
| ----- | -------- | ----- |
| `kind` | yes | Always `DataManagerJobDefinition` |
| `kind-version` | yes | Currently `'2021.1'` |
| `name` | no | A display name for the file/collection |
| `description` | no | Free text |
| `collection` | yes | The collection namespace (see below) |
| `jobs` | yes | A map of Job definitions keyed by Job name |
| `test-groups` | no | Named groups for ordered tests — see [Testing Jobs](testing-jobs.md#test-groups) |

### `collection` and `category`

- **`collection`** is a namespace that groups similar Jobs (e.g. `im-rdkit`).
  A Job is uniquely identified by its *collection*, *name* (the key in the
  `jobs` map) and *version*, so include an organisation identifier in the
  collection name to avoid clashes with Jobs from other authors. Limited to
  80 characters. A Job (name) can appear in more than one collection.
- **`category`** is a functional classification (e.g. `comp chem`) used with
  the collection for filtering in the UI.

### The `jobs` map

Each entry in `jobs` is keyed by the Job's *name* (lower-case letters,
digits and `-`) and supports:

| Field | Required | Notes |
| ----- | -------- | ----- |
| `name` | yes | Display name (max 80 chars) |
| `description` | no | Free text |
| `version` | yes | The Job's version (max 24 chars) — see [Versioning](versioning.md) |
| `category` | no | Functional classification |
| `doc-url` | no | Documentation location (see below) |
| `keywords` | no | List of strings for search/filtering |
| `image` | yes | The container image block (see below) |
| `command-encoding` | no | Always `JINJA2_3_0` (the default and only value) |
| `command` | yes | Jinja2 command template (max 4096 chars) |
| `variables` | no | The inputs/outputs/options declarations (see below) |
| `tests` | no* | Job tests — see [Testing Jobs](testing-jobs.md). *Required in practice: Jobs without tests will not normally be deployed |
| `replaces` | no | List of `{collection, job}` pairs this Job replaces |

### The `image` block

```yaml
image:
  name: informaticsmatters/vs-prep
  tag: 'latest'
  project-directory: /data
  working-directory: /data
  type: simple
  fix-permissions: true
  memory: 2Gi
  cores: 4
```

| Field | Required | Notes |
| ----- | -------- | ----- |
| `name` | yes | The container image (registry) name |
| `tag` | yes | The image tag. `latest` and `stable` are treated as *dynamic* (always pulled); any other tag is treated as *static* — see [Versioning](versioning.md) |
| `project-directory` | yes | Where the DM mounts the user's Project inside the container |
| `working-directory` | yes | The directory the `command` runs in (usually the same as `project-directory`) |
| `type` | no | `simple` (default) or `nextflow` |
| `fix-permissions` | no | If `true` the DM fixes output-file permissions after the Job completes successfully — use this (or `chmod 664` files yourself) so the DM can manage the files your Job creates |
| `pull-secret` | no | Name of a Kubernetes image-pull Secret for private registries |
| `memory` | no | Guaranteed memory budget, e.g. `512Mi`, `2Gi` (used for the Pod's resource request and limit; the DM applies a default if unset) |
| `cores` | no | Guaranteed CPU allocation, e.g. `500m` or `2` |
| `environment` | no | Environment variables injected into the container (see below) |
| `file` | no | Files injected into the container (see below) |

#### Injected environment variables

Each entry names an environment variable and where its value comes from:

```yaml
environment:
- name: GRAPH_SERVER
  value-from:
    secret:
      name: im-fragnet-graph
      key: server
```

The `value-from` variants are:

- `constant: {value: ...}` — a hard-coded value.
- `secret: {name: ..., key: ...}` — a key from an (opaque) Kubernetes Secret
  in the DM namespace.
- `account-server-asset: {name: ...}` — an **Account Server Asset**
  (typically used for licenses).
- `api-token: {roles: [...]}` — a DM API token, with at most one role.

#### Injected files

Files can be materialised in the container, currently only from Account
Server Assets:

```yaml
file:
- name: /usr/local/lib/license.cxl
  content-from:
    account-server-asset:
      name: chemaxon-license
```

### The `command` template

The `command` is a **Jinja2 (v3.0) template**. When a user runs the Job the
Data Manager renders the template with the user's variable values, and the
result is the command executed in the container:

```yaml
command: >-
  /code/max_min_picker.py --input '{{ inputFile }}'
  {% if seeds is defined %}--seeds{% for file in seeds %} '{{ file }}'{% endfor %}{% endif %}
  --output '{{ outputFile }}'
  --count {{ count }}
```

> **Security:** always wrap substituted *string* values in single quotes
> (`'{{ inputFile }}'`) to prevent command-injection through crafted values.

Some *built-in* variables are available during rendering — notably
`DM_INSTANCE_DIRECTORY`, the path of the Job instance's own directory. (When
testing, `jote` also injects `CODE_DIRECTORY` — see
[Testing Jobs](testing-jobs.md#built-in-variables).)

### The `variables` block

`variables` declares what the user must (or may) provide, in a JSON-schema
style. It has four sections:

#### `order`

Controls the display order of options in the UI:

```yaml
variables:
  order:
    options:
    - outputFile
    - count
```

#### `inputs`

Files the Job consumes. The user picks these from their Project files or
Datasets:

```yaml
inputs:
  type: object
  required:
  - inputFile
  properties:
    inputFile:
      title: Molecules to pick from
      mime-types:
      - squonk/x-smiles
      type: file
    multipleFiles:
      title: A multi-valued input
      multiple: true
      mime-types:
      - chemical/x-mdl-sdfile
      type: file
```

`mime-types` restricts what the user can select. Some input *types* are
pre-processed by DM **Job Input Handlers** before the Job runs — see
[Architecture](architecture.md#job-input-handlers).

#### `outputs`

Files the Job creates. `creates` names the file (it may be a template using
option values). Optional `annotation-properties` describe the output in
detail (e.g. a `fields-descriptor` naming and typing every field the file
contains) so downstream tools understand the data:

```yaml
outputs:
  type: object
  properties:
    outputFile:
      title: Output file
      mime-types:
      - chemical/x-csv
      creates: '{{ outputFile }}'
      type: file
```

#### `options`

User-settable parameters, validated as JSON schema (`string`, `integer`,
`number`, `boolean`, enums, `default`, `minimum`/`maximum`, `pattern` ...):

```yaml
options:
  type: object
  required:
  - count
  properties:
    count:
      title: Number of molecules to pick
      type: integer
      minimum: 1
    outputFile:
      title: Output file name
      type: string
      default: diverse.smi
      pattern: "^[A-Za-z0-9_/\\.\\-]+$"
```

By convention, file-name options always carry the
`"^[A-Za-z0-9_/\\.\\-]+$"` pattern to keep names safe.

## Job documentation (`doc-url`)

Each Job should have user documentation, kept in the repository:

- If `doc-url` is **not set**, the DM expects the documentation at
  `data-manager/docs/{collection}/{job-name}.md`.
- If `doc-url` is a **relative path** (starting with a letter, not ending
  `/`), it is resolved under `data-manager/docs/`.
- If `doc-url` starts with **`https`** it is used verbatim.

Keep documentation for all versions of a Job in that Job's single file.

## Validating your files

`jote` validates definitions against the schemas (and applies stricter
formatting rules) — see [Testing Jobs](testing-jobs.md). You can also
validate programmatically:

```python
import yaml
from decoder import decoder  # pip install im-data-manager-job-decoder

with open('data-manager/manifest.yaml') as f:
    error = decoder.validate_manifest_schema(yaml.safe_load(f))
assert error is None, error
```
