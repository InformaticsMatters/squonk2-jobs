# Deploying Jobs

Jobs are loaded into a Data Manager installation by an **administrator**,
who provides the DM with the URL of a Job Manifest. This page covers the
loading mechanics and the pricing (exchange-rate) setup.

## Loading a manifest

The DM API offers admin users an endpoint for Job deployment:

```
PUT /admin/job-manifest
```

Provide the URL (and any optional parameters and header values) of an
online (GitHub/GitLab) manifest and the DM does the rest: it reads each Job
Definition file listed in the manifest and creates (or updates) a Job record
for every Job found.

The URL must be the **raw** file URL. For a public GitHub repository:

```
https://raw.githubusercontent.com/<org>/<repo>/<tag>/data-manager/manifest.yaml
```

The reference can be a branch or a tag, but the two are not equivalent. A
**tag** is a fixed point: reloading the manifest returns the same Job
Definitions it did last time. A **branch** is not — every reload picks up
whatever has since been merged, so Job Definitions change under a deployed
installation without anyone deploying anything. Prefer a tag for anything in
production; see
[Versioning — the three static elements](versioning.md#the-three-static-elements)
and the mode proposal in
[#43](https://github.com/InformaticsMatters/squonk2-jobs/issues/43).

For a **private GitLab** repository use the GitLab API form and provide a
[Personal Access Token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
with `read_repository` capability as a header:

```
URL:    https://gitlab.com/api/v4/projects/<project-id>/repository/files/data-manager%2fmanifest.yaml/raw
HEADER: {'PRIVATE-TOKEN': '<access-token>'}
PARAMS: {'ref': 'main'}
```

Jobs whose container images live in a private registry additionally need an
image-pull Secret in the DM namespace, named by the Job Definition's
`image.pull-secret` field.

Some Jobs have deployment prerequisites of their own — for example a
supporting database in the DM namespace, a Kubernetes Secret providing
connection details, or a license provided as an Account Server **Asset**.
Job repositories should document such requirements; see the notes against
each repository in [Repositories](repositories.md).

## Reloading and Job retention

- Reloading (via `/admin/job-manifest/load`) re-reads all existing manifests
  and their Job Definitions. Definitions whose `collection`, `job` and
  `version` already exist are replaced; new versions create new Job records,
  preserving the old ones — see [Versioning](versioning.md).
- Once a Job is assigned an ID it retains it for the life of the DM.
  Typically, loaded Jobs (and manifests) are not removed — and cannot be
  removed in a production deployment. Manifests can only be removed when the
  Data Manager's **Mode** is `DEVELOPMENT`.

## Exchange Rates

Job pricing is configured with **Exchange Rates**, which convert the
[cost values a Job emits](events-and-costs.md#costs) into **coin** charges:

```
coins = cost * exchange_rate / 1000
```

- Rates are set by an administrator using the DM's exchange-rate API,
  keyed by the Job's **collection**, **name** and **version**.
- A `load_er` utility in the
  [Squonk2 Client Tools](https://github.com/InformaticsMatters/squonk2-python-cl-tools)
  simplifies bulk-loading exchange rates from a YAML file.
- Jobs without an exchange rate are free (coin cost `0`).
- Rates cannot be deleted, but can be set to `0`. Instances always use the
  rate in force when they were launched.

## Repository conventions

- Add the `squonk2-jobs` **Topic** to a repository so it can be identified
  as a Job repository.
- Keep the manifest URL stable — never rename a repository or a manifest
  file once its Jobs are in circulation ([Versioning — Never](versioning.md#never)).

## Our deployed manifests

The list of manifests deployed to Informatics Matters' own installations
(with any special deployment requirements) is maintained on the Data
Manager Wiki's
[Day 1 Jobs](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/day-1-jobs)
page, with initial exchange rates on
[Day 1 Exchange Rates](https://gitlab.com/informaticsmatters/squonk2-data-manager/-/wikis/day-1-rates).
The public Job repositories themselves are catalogued in
[Repositories](repositories.md).
