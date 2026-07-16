# Events and Costs

Jobs communicate with the Data Manager through their **stdout** stream. Two
kinds of specially formatted log lines are recognised:

- **Events** — significant messages presented to the user in the UI.
- **Costs** — usage values that are converted to **coin** charges and sent
  to the Account Server (AS) for billing.

Inside the Data Manager it is the **KEW** Pod that watches Job logs and
detects these lines — see [Architecture](architecture.md).

## Events

A stdout line is treated as an Event when it matches:

```
<datetime> # <level> -EVENT- <message>
```

for example:

```
2022-02-03T16:39:27+00:00 # INFO -EVENT- Hello World!
```

The text after `-EVENT-` is displayed in the Job-execution UI. Typically you
only want a small number of *significant* (salient) events to be reported —
don't turn your entire log into events.

## Costs

A stdout line is treated as a Cost when it matches:

```
<datetime> # <level> -COST- <cost> <seq>
```

for example:

```
2022-02-03T16:40:16+00:00 # INFO -COST- 5.7 1
```

Two values are required:

1. **The cost** — a decimal number in units of your choosing (molecules
   processed, API calls made, ...). Treat costs as *decimals*, not binary
   floating-point, to avoid precision errors (in Python, use `Decimal` — the
   Data Manager does).
2. **The sequence number** — a unique, incrementing integer. The Data
   Manager uses the sequence number to de-duplicate cost lines.

Costs can be expressed in two forms:

- **Absolute** (default): each value replaces the previous one.
  `5.7 1` followed by `8.3 2` yields a final cost of **8.3**.
- **Incremental**: prefix the value with `+` and it is added to the running
  total. `+5.7 1` followed by `+8.3 2` yields a final cost of **14.0**.

## Emitting Events and Costs from Python

The [`im-data-manager-job-utilities`](https://pypi.org/project/im-data-manager-job-utilities/)
package (repository:
[squonk2-data-manager-job-utilities](https://github.com/InformaticsMatters/squonk2-data-manager-job-utilities))
provides the `DmLog` class, which formats the lines correctly and manages
the cost sequence number for you:

```python
from dm_job_utilities.dm_log import DmLog

DmLog.emit_event('Processing', input_file)     # -EVENT- line (level INFO)
DmLog.emit_cost(5.7)                           # absolute -COST- line
DmLog.emit_cost(0.5, incremental=True)         # incremental (+) -COST- line
DmLog.emit_fatal_event('Cannot read input')    # CRITICAL event, then exits(1)
```

Notes:

- `emit_event(..., level=logging.WARNING)` lets you set the level; the
  default is `INFO`.
- `emit_cost()` asserts the cost is a non-negative number and increments the
  sequence number automatically.
- Emission can be disabled (e.g. for local runs) with the environment
  variables `DMLOG_EVENT_DISABLE` and `DMLOG_COST_DISABLE`.

Jobs in other languages simply need to write lines matching the formats
above, with an ISO-8601 timestamp (`%Y-%m-%dT%H:%M:%S%z`).

## How costs become coin charges

A Job's cost lines do not represent a direct financial cost. The financial
cost — expressed in **coins** — is derived from the cost using the Job's
**Exchange Rate**:

```
coins = cost * exchange_rate / 1000
```

The built-in scale factor of `1000` avoids having to express exchange rates
as very small fractions.

Key behaviour:

- Exchange rates apply to individual Job definitions and are keyed by the
  Job's **collection**, **name** and **version**.
- Exchange rates are set by an administrator using the DM's exchange-rate
  API — see [Deploying Jobs](deploying-jobs.md#exchange-rates).
- **If a Job has no exchange rate, its coin cost is zero** — there is no
  charge for running it.
- Each Job Instance uses the exchange rate that applied when it was
  launched; later changes only affect new instances.
- Exchange rates cannot be removed, but setting a rate to `0` removes any
  future coin cost. All historical rates are retained (with author, time,
  and an optional comment).

Behind the scenes, accumulated coins are charged to the user's Account
Server **Product**: the KEW detects cost lines, charges are recorded in the
DM database, and the MON Pod transmits them to the Account Server
(retrying if the AS is unavailable). See
[Architecture](architecture.md) for the Pod-level detail.
