# Job Definition Schema — Coverage Holes

This document reports where real **Job Definition** files use content that the
Job Definition **schema** does not explicitly cover — the "holes" requested by
[issue #8](https://github.com/InformaticsMatters/squonk2-jobs/issues/8).

The schema is the authoritative JSONSchema (draft-07) at
`squonk2-data-manager-job-decoder/decoder/job-definition-schema.yaml`. Ideally
it describes the *entire* content of a Job Definition; in practice a handful of
objects omit `additionalProperties: false`, so unknown keys pass validation
silently, and one real file uses keys the schema does not model at all.

## Method

- Every file in the umbrella repository containing
  `kind: DataManagerJobDefinition` was collected — **18 files** (the decoder's
  own `example-definitions/` are excluded as they are fixtures, not deployed
  Jobs).
- Each file was validated against the schema with a Draft7 validator, and its
  keys were separately walked (top-level, `job`, `image`, `variables`, `tests`)
  to catch keys the schema *silently* accepts because the enclosing object has
  no `additionalProperties: false`.

**Result: 17 of the 18 files fully conform.** Every finding below comes from a
single file, `virtual-screening/data-manager/moldb.yaml`, but each one exposes a
genuine gap in what the schema describes.

## Summary of holes

| # | Location in schema | Kind | Real example | Recommendation |
| - | ------------------ | ---- | ------------ | -------------- |
| 1 | Top-level object (`properties:`, ~line 15) | Silent — no `additionalProperties: false` | `repository-url`, `repository-tag` (`moldb.yaml:6-7`) | Add `additionalProperties: false`; model or drop the two keys |
| 2 | `job` object (`definitions.job`, ~line 58) | Silent — no `additionalProperties: false` | `options:` on the job itself in `moldb-count-rows` (`moldb.yaml:113`) | Add `additionalProperties: false` |
| 3 | `job-option-property` (~line 574) | Hard fail — keys not modelled | `minValue` / `maxValue` (`moldb.yaml:274-275` + 8 more) | Model `minValue`/`maxValue`, or correct jobs to `minimum`/`maximum` |
| 4 | `checks` (~line 662), `test-checks-output` (~line 715), `value-from` inner objects | Silent — no `additionalProperties: false` | none currently | Add `additionalProperties: false` for consistency |

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

### Hole 3 — option `minValue` / `maxValue` are not modelled (hard fail)

`job-option-property` models numeric bounds as `minimum` / `maximum` and *does*
set `additionalProperties: false`. Several options in `moldb.yaml` instead use
`minValue` / `maxValue`:

```yaml
chunk_size:
  title: Chunk size for splitting
  type: integer
  default: 100000
  minValue: 10000
  maxValue: 1000000
```

This is the one place where a live Job Definition is **rejected** by the schema
(9 validation errors, see below). The schema needs either to model
`minValue`/`maxValue` or the job needs correcting to `minimum`/`maximum`.

### Hole 4 — other objects missing `additionalProperties: false` (latent)

For completeness, the same class of silent hole exists in the `checks` object,
`test-checks-output`, and the four `value-from` inner objects (`api-token`,
`constant`, `secret`, `account-server-asset`). No current Job exploits these,
but they would accept unknown keys just like holes 1 and 2.

## Recommended schema extensions

1. Add `additionalProperties: false` to the **top-level object** and the **`job`
   object** (holes 1, 2) — and, for consistency, to the objects in hole 4.
2. Decide the intent of `minValue` / `maxValue` (hole 3): either add them to
   `job-option-property` or fix `moldb.yaml` to use `minimum` / `maximum`.
3. Decide the intent of `repository-url` / `repository-tag` (hole 1): either add
   them to the top-level object or remove them from `moldb.yaml`.

Schema changes live in the `squonk2-data-manager-job-decoder` submodule and must
be made there via its own pull request; this document only reports the holes.

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

The only file that produces output is `moldb.yaml`:

```
moldb.yaml ['jobs', 'moldb-calc-props', 'variables', 'options', 'properties', 'chunk_size'] | Additional properties are not allowed ('maxValue', 'minValue' were unexpected)
moldb.yaml ['jobs', 'moldb-calc-props', 'variables', 'options', 'properties', 'count'] | Additional properties are not allowed ('maxValue' was unexpected)
moldb.yaml ['jobs', 'moldb-enumerate-mols', 'variables', 'options', 'properties', 'chunk_size'] | Additional properties are not allowed ('maxValue', 'minValue' were unexpected)
moldb.yaml ['jobs', 'moldb-enumerate-mols', 'variables', 'options', 'properties', 'count'] | Additional properties are not allowed ('maxValue' was unexpected)
moldb.yaml ['jobs', 'moldb-extract-confs', 'variables', 'options', 'properties', 'count'] | Additional properties are not allowed ('maxValue' was unexpected)
moldb.yaml ['jobs', 'moldb-extract-enums', 'variables', 'options', 'properties', 'count'] | Additional properties are not allowed ('maxValue' was unexpected)
moldb.yaml ['jobs', 'moldb-gen-confs', 'variables', 'options', 'properties', 'chunk_size'] | Additional properties are not allowed ('maxValue', 'minValue' were unexpected)
moldb.yaml ['jobs', 'moldb-gen-confs', 'variables', 'options', 'properties', 'count'] | Additional properties are not allowed ('maxValue' was unexpected)
moldb.yaml ['jobs', 'moldb-load-library', 'variables', 'options', 'properties', 'chunk_size'] | Additional properties are not allowed ('maxValue', 'minValue' were unexpected)
```

The silent holes (1, 2, 4) produce **no** validation errors — that is precisely
why they are holes.
