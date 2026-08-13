# Architecture — how the Data Manager runs Jobs

This page describes what happens inside the Data Manager (DM) when a Job
runs, at the depth a Job author needs. Deeper DM internals are documented in
the (private) Data Manager Wiki.

The Data Manager is a containerised application deployed to **Kubernetes**.
Jobs are *short-lived* **Instances**: each Job execution becomes a Pod in
the DM's namespace, with the user's **Project** directory mounted as its
source of data.

## The Pods involved in a Job's life

The DM is composed of several cooperating Pods. Four matter to Job authors:

### API

The DM's REST API. When a user launches a Job the `api` Pod validates the
request against the Job Definition (using the
[Job Decoder](repositories.md#squonk2-data-manager-job-decoder)), applies
any [input handlers](#job-input-handlers), records the launch exchange rate
in the new **Instance**, and delegates execution.

### CTW — the Celery Task Worker

The **CTW** executes the DM's asynchronous tasks — including launching Job
Pods (via the [Job Operator](repositories.md#squonk2-data-manager-job-operator))
and monitoring their initial lifecycle. Installations can run more than one
CTW to scale concurrent task execution.

### KEW — the Kubernetes Event Watcher

The **KEW** watches the Instance Pods running in the DM's namespace. For
each Pod it:

- detects Pod state/phase changes (start, exit, failure), and
- collects the Pod's log — detecting the
  [`-EVENT-` and `-COST-` lines](events-and-costs.md) in the Job's stdout
  and creating Event and Cost records from them.

Because Job output formats differ, `simple` and `nextflow` Job logs are
handled by different functions.

Pod state changes are forwarded (as messages) to the **PBC** (Protocol
Buffer Consumer) Pod, which performs the time-consuming follow-up actions —
including generating the final "End of Charge" cost message that tells the
Account Server the Job has finished and final costs can be calculated.

### MON — the monitor

The **MON** is the DM's general-purpose housekeeping Pod. Among its duties
it regularly (roughly every 60 seconds) checks for coin **charges** that
have not yet been sent to the **Account Server** and transmits them,
removing each record once the AS acknowledges it. If the AS is unavailable,
or a charge is rejected, transmission stops and resumes on the next cycle.

## The cost pipeline, end to end

1. The Job writes a `-COST-` line to stdout
   ([format](events-and-costs.md#costs)).
2. The KEW detects the line and records the cost against the Instance.
3. The cost is converted to **coins** using the Instance's launch
   [exchange rate](deploying-jobs.md#exchange-rates)
   (`coins = cost * rate / 1000`).
4. A charge record is created in the DM database (via the PBC).
5. The MON transmits outstanding charges to the Account Server, where they
   are billed against the user's **Product**.

## Job launch and images

The Job's Pod is created by the cluster-level
[Job Operator](repositories.md#squonk2-data-manager-job-operator). The
Job Definition's `image` block controls the container: the project
directory mount point, working directory, optional memory/cores resource
guarantees, injected environment variables and files, and the image tag —
where `latest`/`stable` tags are treated as *dynamic* and always re-pulled
before execution, and any other tag is treated as *static* and cached per
node (see
[Versioning](versioning.md#how-the-data-manager-treats-image-tags)).
A dynamic tag is a development convenience: it is designed to change
underneath a Job, so it gives no reproducibility guarantee.

After a successful run, if the definition sets
`image.fix-permissions: true`, the DM fixes the permissions of the files
the Job created so they are manageable by the DM.

## Job Input Handlers

**Job Input Handlers** provide input-parameter filtering and adaptation for
Job input data, and can simplify Job implementations. An input handler
modifies an Instance input variable's *value* based on the input's declared
*type*, before the Job runs — pre-processing that would otherwise have to be
repeated inside every Job.

Handlers are part of the Data Manager itself (one handler per input type).
The DM's `GET /input-handler` API endpoint lists the installed handlers,
the input types they handle, and their documentation.

For a Job author the practical implication is: the value your command
template receives for an input may have been adapted by a handler
registered for that input's type. Consult `/input-handler` on the target
installation to see what applies.
