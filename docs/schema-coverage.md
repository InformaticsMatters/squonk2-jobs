# Job Definition Schema — Coverage Holes

This document reports where real **Job Definition** files use content that the
Job Definition **schema** does not explicitly cover — the "holes" requested by
[issue #8](https://github.com/InformaticsMatters/squonk2-jobs/issues/8).

The schema is the authoritative JSONSchema (draft-07) at
`squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml`. Ideally
it describes the *entire* content of a Job Definition; in practice a few objects
omit `additionalProperties: false`, so unknown keys pass validation silently.

> **Checked against decoder `2.7.0`** — the version pinned by
> `DECODER_VERSION` in `.github/workflows/test-jobs.yaml` and vendored as the
> `squonk2-data-manager-job-decoder` submodule. The schema lives in the decoder,
> so **the answers here change when the decoder does**; re-run the analysis
> below after any decoder bump.

## Method

- Every file in the umbrella repository containing
  `kind: DataManagerJobDefinition` was collected — **18 files** (the decoder's
  own `example-definitions/` are excluded as they are fixtures, not deployed
  Jobs).
- Each file was validated against the schema with a Draft7 validator, and its
  keys were separately walked (top-level, `job`, `image`, `variables`, `tests`)
  to catch keys the schema *silently* accepts because the enclosing object has
  no `additionalProperties: false`.

**Result: all 18 files validate cleanly — zero errors.** That is an improvement
on the original survey (17 of 18) but it does not mean the schema now describes
everything: the remaining holes are *silent* by nature, so a clean run is
exactly what they produce.

## Summary of holes

| # | Location in schema | Kind | Real example | Status |
| - | ------------------ | ---- | ------------ | ------ |
| 1 | Top-level object (`properties:`, line 15) | Silent — no `additionalProperties: false` | `repository-url`, `repository-tag` (`moldb.yaml:6-7`) | **Open** |
| 2 | `job` object (`definitions.job`, line 58) | Silent — no `additionalProperties: false` | `options:` on the job itself in `moldb-count-rows` | **Open** |
| 3 | `job-option-property` (line 645) | Hard fail — keys not modelled | `minValue` / `maxValue` in `moldb.yaml` | **Closed** — the Jobs were corrected |
| 4 | `test-checks-output` (line 820) | Silent — no `additionalProperties: false` | none | **Open** |
| 4a | `value-from` inner objects (now `environment-value-from-*`) | Silent | none | **Closed** in the decoder |
| 5 | `annotation-properties` (line 551) | **Explicitly** `additionalProperties: true` | misplaced `derived-from` (see below) | **Closed** in 2.7.0 |
| 6 | Option `items` (now `job-option-property-items`, line 687) | **Explicitly** `additionalProperties: true` | none | **Closed** in 2.7.0 |

Holes 5 and 6 were not in the original survey. They are a distinct and more
serious class: those objects did not merely *omit* `additionalProperties`, they
declared `additionalProperties: true` — free-form by design, so the key-walking
method had nothing to flag.

## Details

### Hole 1 — top-level object accepts unknown keys (silent)

The root object lists `kind`, `name`, `description`, `collection`, `jobs` and
`test-groups` but does **not** set `additionalProperties: false`. Any unknown
top-level key therefore validates. `moldb.yaml` uses two such keys:

```yaml
repository-url: https://github.com/InformaticsMatters/virtual-screening/moldb.yaml
repository-tag: '1.0.0'
```

Neither `repository-url` nor `repository-tag` appears in any other Job
Definition, in the documentation, or in the decoder source. They are either a
convention that should be formalised in the schema or a mistake that the schema
should reject — today it does neither.

### Hole 2 — `job` object accepts unknown keys (silent)

The `job` definition lists its properties (`name`, `version`, `image`,
`command`, `variables`, `tests`, …) but likewise omits
`additionalProperties: false`. In `moldb-count-rows` an `options:` block is
placed **directly on the job** instead of under `variables:`:

```yaml
moldb-count-rows:
  name: MolDB count rows
  ...
  options:            # <-- should be variables.options
    type: object
    required:
    - table
```

Because the schema accepts the stray key, the misplaced options are silently
ignored rather than flagged.

### Hole 3 — option `minValue` / `maxValue` (closed)

`job-option-property` models numeric bounds as `minimum` / `maximum` and *does*
set `additionalProperties: false`. Several options in `moldb.yaml` used
`minValue` / `maxValue`, producing the 9 validation errors that made this the
one *hard* failure in the original survey.

**Closed by correcting the Jobs, not the schema.** `moldb.yaml` no longer
contains `minValue` or `maxValue` anywhere, and `job-option-property` still
models only `minimum` / `maximum`. Of the two options the original
recommendation offered, the "fix the Jobs" branch was taken — which is the right
one, since `minValue`/`maxValue` were never a convention, just a mistake.

### Hole 4 — other objects missing `additionalProperties: false` (partly closed)

The four `value-from` inner objects are now `environment-value-from-api-token`,
`-constant`, `-secret` and `-account-server-asset`, and **all four now set
`additionalProperties: false`**, as do `test-checks-output-exists` and
`test-checks-output-linecount`.

**One remains open:** `test-checks-output` (line 820), whose `checks` and `name`
properties sit in an object that still accepts unknown keys. There is no
separate `checks` object — the original survey's reference to one was really to
this object's `checks` property.

### Holes 5 and 6 — the free-form objects closed by decoder 2.7.0

Two objects were declared `additionalProperties: true`. That is worse than
omitting the keyword: it is an explicit statement that anything goes, so no
amount of key-walking will flag content inside them. Decoder **2.7.0**
(released 2026-08-13) replaced both with modelled definitions:

| Was | Now | New sub-definitions |
| --- | --- | ------------------- |
| `annotation-properties: {additionalProperties: true}` | `annotation-properties` with `additionalProperties: false` | `fields-descriptor-annotation`, `fields-descriptor-field`, `service-execution-annotation` |
| option `items: {additionalProperties: true}` | `job-option-property-items` with `additionalProperties: false` | `job-option-property-items-choice` |

**Closing hole 5 immediately found a real bug.** `similarity-screen-rdkit` in
`virtual-screening/data-manager/rdkit.yaml` had `derived-from` nested one level
too deep, inside `fields-descriptor` rather than alongside it under
`annotation-properties` — an indentation slip that had been invisible for as
long as the block was free-form. The output had been shipping a
`fields-descriptor` with a stray key and no `derived-from` annotation at all.
Fixed in
[virtual-screening#30](https://github.com/InformaticsMatters/virtual-screening/pull/30).

This is the central argument of this document, demonstrated: a silently
permissive schema does not mean the Job Definitions are correct, only that
nobody is checking.

It also arrived as an unrelated CI failure, because the decoder was an unpinned
transitive dependency of `jote`. It is now pinned — see the note at the top of
this page, and #48.

## Recommended schema extensions

1. Add `additionalProperties: false` to the **top-level object** (hole 1), the
   **`job` object** (hole 2), and **`test-checks-output`** (hole 4). These are
   the only object definitions in the schema that still lack it.
2. Decide the intent of `repository-url` / `repository-tag` (hole 1): either add
   them to the top-level object or remove them from `moldb.yaml`.
3. Fix the misplaced `options:` block on `moldb-count-rows` (hole 2), which is
   silently ignored today. Closing hole 2 would turn it into a hard failure, so
   the Job should be corrected first — the sequencing that holes 5 and 6 showed
   matters.

Schema changes live in the `squonk2-data-manager-job-decoder` submodule and must
be made there via its own pull request; this document only reports the holes.

Note the lesson from 2.7.0 for whoever does the above: closing a hole can fail
Job Definitions that have been passing for years, and — because the decoder is
shared — it does so for everybody at once. Pair each closure with a survey of
what it would newly reject, and land the Job fixes first.

## Reproducing the analysis

Validate every Job Definition against the schema:

```python
import yaml, subprocess, jsonschema
schema = yaml.safe_load(open(
    'squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml'))
files = subprocess.check_output(
    "grep -rl 'kind: DataManagerJobDefinition' --include='*.yaml' . "
    "| grep -v job-decoder/example", shell=True, text=True).split()
validator = jsonschema.Draft7Validator(schema)
for f in sorted(files):
    for e in validator.iter_errors(yaml.safe_load(open(f))):
        print(f, list(e.path), '|', e.message)
```

Against decoder 2.7.0 this now produces **no output at all** — all 18 files
validate. (Before hole 3 was closed it printed 9 errors, all from `moldb.yaml`,
all `minValue`/`maxValue`.)

A clean run is not evidence of coverage. The remaining holes are silent by
definition, so listing the objects that still accept unknown keys is the more
useful check:

```python
import yaml
schema = yaml.safe_load(open(
    'squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml'))
if 'additionalProperties' not in schema:
    print('root object')
for name, obj in sorted(schema['definitions'].items()):
    if (isinstance(obj, dict) and obj.get('type') == 'object'
            and 'properties' in obj and 'additionalProperties' not in obj):
        print(name)
```

Which currently reports exactly three — the three in the recommendations above:

```
root object
job
test-checks-output
```

Also worth grepping for the free-form class that holes 5 and 6 belonged to,
since it is invisible to both checks:

```bash
grep -n 'additionalProperties: true' \
    squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml
```

This currently returns nothing.
