# Shared Python Helpers

Two published packages are the **canonical home** for helper code shared by
Python Jobs. Job repositories import from them; they must not carry their own
copies.

| Package | Import as | Holds |
| ------- | --------- | ----- |
| [`im-data-manager-job-utilities`](https://pypi.org/project/im-data-manager-job-utilities/) | `dm_job_utilities` | Data Manager concerns — Events, Costs, progress reporting, and generic file/string helpers |
| [`im-rdkit-utilities`](https://pypi.org/project/im-rdkit-utilities/) | `rdkit_utils` | RDKit concerns — molecule readers and writers, fragment selection, and the command-line options that feed them |

`im-rdkit-utilities` depends on `im-data-manager-job-utilities`, so a Job
needing both can depend on the RDKit package and get the other transitively.
A Job that does no RDKit work should depend only on the job-utilities package.

## Which package does a helper belong in?

The dividing line is what the helper is *about*, not which Job happens to use
it:

- Anything the **Data Manager** interprets — Event lines, Cost lines, progress
  reporting — belongs in `dm_job_utilities`.
- Anything describing **molecules or molecule files** belongs in `rdkit_utils`,
  next to the readers and writers it serves.

The `--interval` option is the worked example. It looks like an I/O option and
sat with them historically, but it exists only to pace
`DmLog.emit_event("Processed N records")`, so it lives in `dm_job_utilities`
alongside `ProgressReporter` — not in the molecule I/O group.

## `dm_job_utilities`

### Events and costs

`DmLog.emit_event()` and `DmLog.emit_cost()` — see
[Events and Costs](events-and-costs.md).

### Progress reporting

`add_reporting_args(parser)` adds the `--interval` option; `ProgressReporter`
wraps the interval-based reporting idiom:

```python
from dm_job_utilities.cli import ProgressReporter, add_reporting_args

add_reporting_args(parser)                    # or interval_default=1000
args = parser.parse_args()

reporter = ProgressReporter(args.interval)
for count, record in enumerate(records, start=1):
    ...
    reporter.report(count)
reporter.report_final(count)                  # closing event plus final cost
```

`--interval` defaults to `None`, meaning no progress events unless the Job is
run with the option. Pass `interval_default` for Jobs that should report by
default. Only add these if the Job has a per-record loop — a Job that reads its
input in one pass has nothing to report, and an accepted-but-ignored option is
worse than no option.

### Generic helpers

`dm_job_utilities.utils` provides `log`, `expand_path`, `read_delimiter`,
`is_type`, `calc_geometric_mean`, `write_row` and
`update_charge_flag_in_atom_block`.

Two functions that Jobs used to carry locally are deliberately **absent**:

- `get_path_from_digest()` — dropped as obsolete. A Job that still needs a
  digest-to-directory mapping should keep its own.
- `round_to_significant_number()` — dropped; its implementation inherited
  `round()`'s half-way behaviour (`2.675` → `2.67`). Use
  [`sigfig`](https://pypi.org/project/sigfig/)'s `round(value, sigfigs=n)`
  instead, passing `warn=False` to stay quiet when a value carries fewer
  significant figures than requested.

## `rdkit_utils`

### Readers and writers

`create_reader()` and `create_writer()` pick an SDF or delimited-SMILES
implementation from the file extension. See the package README for the full
surface.

### Molecule I/O command-line options

`add_common_molecule_io_args(parser)` adds the "Input/output options" group
that most molecule-processing Jobs need, so it is written once rather than
re-typed per Job:

`-i/--infile`, `-o/--outfile`, `-d/--delimiter`, `--id-column`,
`--mol-column`, `--read-header`, `--write-header`, `--read-records`,
`-k/--omit-fields`, and `--y-column` when `include_y_column=True`.

```python
import rdkit_utils
from dm_job_utilities.utils import read_delimiter

rdkit_utils.add_common_molecule_io_args(parser, output_required=True)
args = parser.parse_args()

reader = rdkit_utils.create_reader(
    args.input,
    delimiter=read_delimiter(args.delimiter),
    read_header=args.read_header,
    id_column=args.id_column,
    mol_column=args.mol_column,
    read_records=args.read_records,
)
```

Keyword arguments cover the variation between Jobs: `output_default`,
`output_required` and `include_y_column`.

`--infile` and `--outfile` are the **canonical long spellings**. `--input` and
`--output` are accepted as aliases so that adopting the helper does not break
existing Job Definitions, and the parsed values are always `args.input` and
`args.output`. The aliases will not be kept indefinitely.

In a Job Definition's `command` block, prefer the short forms **`-i` and
`-o`**. They are canonical, they survive the removal of the long aliases, and
— unlike `--infile`/`--outfile` — they also work against container images
built *before* the Job adopted the helper. That last point matters more than
it looks: a Job Definition is loaded against whatever image tag it pins, so a
definition written with `--infile` fails until an image carrying the migrated
script is published. Using `-i`/`-o` removes the ordering dependency entirely.

`str_or_int` is the argparse type used for the column options — a column may be
given as a zero-based index or as a field name.

### When *not* to use the I/O group

It is a poor fit for a Job that:

- **Spells the options differently.** Adopting it would rename public options
  and force a Job Definition change.
- **Uses a different short flag.** `-d` belongs to `--delimiter`; a Job using
  `-d` for something else must free it first or leave the group alone.
- **Indexes columns with pandas** rather than through `create_reader()`. The
  group types its column options as `str_or_int` and defaults them to `None`,
  which breaks positional `df.iloc[:, n]` access.

Taking a group that mostly fits and then fighting its defaults is worse than
declaring the options the Job actually wants.

## Adding to these packages

Add a helper when a second Job needs it, not in anticipation. Put it in the
package matching the dividing line above, with tests. Consumers then pin a
minimum version — avoid exact `==` pins in a Job, and never in a library: an
exact pin in `im-rdkit-utilities` once made it uninstallable alongside a current
`im-data-manager-job-utilities`.
