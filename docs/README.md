# Squonk2 Data Manager Jobs — Documentation

This is the **authoritative** home for all documentation relating to Squonk2
Data Manager (DM) **Jobs**. Other repositories enforce or follow what is
written here — they must not duplicate it.

## Who is this for?

- **Job authors** — people writing new Jobs (their own tools, containers, and
  Job Definitions) for use in a Data Manager. Start with the
  [Getting Started guide](getting-started.md).
- **DM administrators** — people loading Jobs into a Data Manager installation
  and setting their pricing. See [Deploying Jobs](deploying-jobs.md).
- **DM developers** — people working on the Data Manager itself. The
  author-facing view of the runtime is in [Architecture](architecture.md);
  deeper internals remain in the (private) Data Manager Wiki.

## Contents

| Document | What it covers |
| -------- | -------------- |
| [Getting Started](getting-started.md) | The end-to-end tutorial: tool → container image → Job Definition → tests → deployment |
| [Job Definitions](job-definitions.md) | Reference for Job Manifest and Job Definition YAML files |
| [Testing Jobs](testing-jobs.md) | Functional testing with `jote`, the Job Tester |
| [Events and Costs](events-and-costs.md) | Emitting Events and Costs from a Job, and how costs become coin charges |
| [Versioning](versioning.md) | Versioning Job Definitions and container images safely |
| [Deploying Jobs](deploying-jobs.md) | Loading manifests into a Data Manager and setting exchange rates |
| [Architecture](architecture.md) | How the Data Manager runs Jobs (CTW, KEW, MON, input handlers) |
| [Repositories](repositories.md) | Catalogue of all Job-related repositories and packages |

## Nomenclature

A few terms used throughout this documentation:

- A **Job** is a single executable "task" in the Data Manager.
- A Job is uniquely identified by a **Collection** name, a **Name**, and a
  **Version**.
- A Job's properties and behaviour are defined in a **Job Definition** file
  (YAML).
- **Job Manifest** files (YAML) provide grouping, and list all the Job
  Definition files that belong to the group.
- Jobs are *loaded* into a Data Manager installation by an administrator who
  provides the DM with the URL of the author's Job Manifest. The DM then reads
  each Job Definition file in the manifest and creates (or updates) a Job
  record for each Job found.
- Jobs can generate **Events** — specially formatted stdout log messages that
  the DM collects and presents to the user in the UI.
- Jobs can generate **Costs** — specially formatted stdout log messages that
  the DM collects and transmits to the **Account Server** (AS) for billing.

## The 60-second overview

1. Jobs are distributed as a **container image**.
2. **Job Definitions** (and **Job Manifests**) typically co-habit the
   repository where the Job logic can be found.
3. Manifests and definitions must be placed in a `data-manager` directory of
   the repository.
4. The URL of the manifest is used when loading Jobs into a Data Manager.
5. A single definition file can describe more than one Job or, depending on
   the author's needs, separate files can be used for each Job. Jobs that
   would normally be deployed together are considered part of a common group.
6. Job pricing is configured using **Exchange Rates**, set by an administrator
   using the DM API.
7. By convention, Job repositories are easier to identify because the
   `squonk2-jobs` **Topic** is added to the repository.
8. Inside the Data Manager, the **CTW** Pod launches Jobs (and monitors their
   initial lifecycle), the **KEW** Pod monitors Jobs — watching for exit state
   and collecting Event and Cost lines — and the **MON** Pod sends Job cost
   information to the Account Server.
