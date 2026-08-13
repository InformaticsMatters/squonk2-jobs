# Job Definition Schema — Coverage Holes

This document reports where real **Job Definition** files use content that the
Job Definition **schema** does not explicitly cover — the "holes" requested by
[issue #8](https://github.com/InformaticsMatters/squonk2-jobs/issues/8).

The schema is the authoritative JSONSchema (draft-07) at
`squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml`. Ideally
it describes the *entire* content of a Job Definition.

> ## ✅ All known holes are closed as of decoder `2.8.0`
>
> **No object in the schema accepts unknown keys**, and none is declared
> `additionalProperties: true`. Every Job Definition in every Job repository
> validates cleanly.
>
> This page is kept as the record of what the holes were, what they cost, and
> how to check the position again — not as a list of outstanding work.

> **Checked against decoder `2.8.0`** — the version pinned by
> `DECODER_VERSION` in `.github/workflows/test-jobs.yaml` and vendored as the
> `squonk2-data-manager-job-decoder` submodule. The schema lives in the decoder,
> so **the answers here change when the decoder does**; re-run the analysis
> below after any decoder bump, and move the two together.

## Method

- Every file in the umbrella repository containing
  `kind: DataManagerJobDefinition` was collected — **18 files** (the decoder's
  own `example-definitions/` are excluded as they are fixtures, not deployed
  Jobs).
- Each file was validated against the schema with a Draft7 validator, and its
  keys were separately walked (top-level, `job`, `image`, `variables`, `tests`)
  to catch keys the schema *silently* accepts because the enclosing object has
  no `additionalProperties: false`.

**Result: all 18 files validate cleanly — zero errors**, against a schema in
which no object accepts unknown keys. Under 2.7.0 and earlier a clean run proved
much less, because the silent holes produced clean runs by definition.

## Summary of holes

| # | Location in schema | Kind | Real example | Closed by |
| - | ------------------ | ---- | ------------ | --------- |
| 1 | Top-level object | Silent — no `additionalProperties: false` | `repository-url`, `repository-tag` in `moldb.yaml` | Jobs corrected, then decoder **2.8.0** |
| 2 | `job` object | Silent — no `additionalProperties: false` | `options:` directly on `moldb-count-rows` | Jobs corrected, then decoder **2.8.0** |
| 3 | `job-option-property` | Hard fail — keys not modelled | `minValue` / `maxValue` in `moldb.yaml` | the Jobs being corrected |
| 4 | `test-checks-output` | Silent — no `additionalProperties: false` | none | decoder **2.8.0** |
| 4a | `value-from` inner objects (now `environment-value-from-*`) | Silent | none | the decoder |
| 5 | `annotation-properties` | **Explicitly** `additionalProperties: true` | misplaced `derived-from` (see below) | decoder **2.7.0** |
| 6 | Option `items` (now `job-option-property-items`) | **Explicitly** `additionalProperties: true` | none | decoder **2.7.0** |

Holes 5 and 6 were not in the original survey. They are a distinct and more
serious class: those objects did not merely *omit* `additionalProperties`, they
declared `additionalProperties: true` — free-form by design, so the key-walking
method had nothing to flag.

### The pattern worth remembering

Every hole that a live Job Definition exploited had to be closed in **two steps,
in order**: correct the Jobs, *then* tighten the schema. Reversing that order
breaks every consumer at once, because the decoder is a shared dependency — which
is exactly what 2.7.0 did, failing two unrelated documentation merges here.

The three offending Jobs were fixed in
[virtual-screening#32](https://github.com/InformaticsMatters/virtual-screening/pull/32),
[#33](https://github.com/InformaticsMatters/virtual-screening/pull/33) and the
earlier `minValue`/`maxValue` correction, and the schema was tightened only once
all of them had landed.

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

### Hole 4 — other objects missing `additionalProperties: false` (closed)

The four `value-from` inner objects are now `environment-value-from-api-token`,
`-constant`, `-secret` and `-account-server-asset`, and all four set
`additionalProperties: false`, as do `test-checks-output-exists` and
`test-checks-output-linecount`.

`test-checks-output` itself was the last of them, closed in decoder **2.8.0**.
There is no separate `checks` object — the original survey's reference to one was
really to this object's `checks` property.

No Job exploited this hole, so it is the only one closed purely for consistency
rather than in response to a defect.

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

## If a new hole appears

Schema changes live in the `squonk2-data-manager-job-decoder` submodule and must
be made there via its own pull request; this document only reports the position.

The procedure that worked, and should be repeated:

1. **Survey what the closure would newly reject**, across every Job repository —
   not just the one that prompted it.
2. **Fix the Job Definitions first**, each with a version bump if behaviour
   changes, and let them merge.
3. **Then tighten the schema**, with a `bad` fixture per closure so the
   behaviour is covered by tests rather than by careful reading.
4. **Release it deliberately**, with notes naming what is newly rejected.
   Consumers that pin the decoder choose when to take it; consumers resolving it
   transitively do not.
5. **Bump `DECODER_VERSION` and the submodule pointer together**, so the
   vendored schema and the version CI installs cannot drift apart — this
   document's checks read the vendored copy.

Skipping step 1 or 2 breaks every consumer at once. That is not hypothetical:
2.7.0 was released without them and failed two unrelated documentation merges in
this repository, on a day nobody had touched a Job Definition.

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

Against decoder 2.8.0 this produces **no output at all** — all 18 files validate.
(Before hole 3 was closed it printed 9 errors, all from `moldb.yaml`, all
`minValue`/`maxValue`.)

That result now means something. Under 2.7.0 and earlier it did not: the silent
holes produced clean runs by construction, so the useful check was to list the
objects that accept unknown keys. Keep running it — it is what will catch a
regression, or a newly added object that forgets the keyword:

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

Against 2.8.0 this reports **nothing** — no object accepts unknown keys. Any name
it prints in future is a new hole.

Also grep for the free-form class that holes 5 and 6 belonged to, since it is
invisible to both checks above — an object can set `additionalProperties: true`
and pass everything:

```bash
grep -n 'additionalProperties: true' \
    squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml
```

This also returns nothing against 2.8.0.
