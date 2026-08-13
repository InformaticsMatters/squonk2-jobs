# Versioning Jobs

To use Jobs in a safe and repeatable way you need to version them. The goal is
a simple one: **a Job that ran in July must still run, and give the same
results, in December.**

Meeting that goal means keeping three things static.

## The three static elements

| Element | Where it lives | What breaks if it moves |
| ------- | -------------- | ----------------------- |
| The **manifest URL** | The URL an administrator gives the DM (see [Deploying Jobs](deploying-jobs.md)) | The set of Job Definitions, and their contents, change under a deployed installation |
| The Job's **`version`** | The Job Definition at that URL | The DM replaces the existing Job record rather than creating a new one |
| The **image tag** | The Job Definition's `image.tag` | The implementation changes while the Job version claims it has not |

All three matter, and they fail independently. A Job Definition can pin an
immutable image tag and still drift, because its *manifest* was loaded from a
branch that keeps moving.

When you reach a point of stability with your Job you should protect your work
by versioning it. A strict versioning policy will inevitably slow down your
development throughput, but without it you risk not being able to re-run
valuable experiments — or, worse, breaking or silently altering the behaviour
of Jobs already in circulation.

To version a Job, consider what changed. That dictates whether you need to
adjust the Job Definition version, or the Job Definition version *and* the
container image tag.

## Recommended numbering styles

There are no rules, but two accepted standards:

- **[Semantic Versioning 2.0.0](https://semver.org)** — select the next
  appropriate **MAJOR.MINOR.PATCH** value that represents your change.
- **YEAR.PATCH** (e.g. `2022.1`) — suited to software that simply "gets
  better". The next release in the same year is `2022.2`; the first release
  of the following year is `2023.1`.

You do not have to use the same style for the Job Definition version as for
the container image tag, but you should apply a strict and disciplined
policy about changing them. Get into the habit of changing versions whenever
you adjust, enhance or fix the implementation in any way.

## Changes to the Job Definition only

Here you have not altered the Job implementation (the content of the
container image) — just the YAML *definition* of the Job. Examples include
any change to the `variables` block, the `command`, or the `image` block.

1. Change the Job's `version` value in the YAML file and commit.
2. Ask an administrator of each Data Manager installation where the Job is
   in use to trigger a re-load via the DM's `/admin/job-manifest/load`
   endpoint, which reloads all existing manifests and their Job Definitions.

## Changes to the Job code (anything in the container image)

Here you have altered anything that changes the run-time behaviour compiled
into the container image:

1. Publish a new container image with a new tag. Ideally change the tag for
   *every* new image you build and use — even the slightest change can alter
   run-time behaviour.
2. Change the versions of **all** the Job Definitions that use the new
   image. If one image is used by seven Jobs, changing the image means
   changing all seven Job versions. This protects you — and the Job's users —
   from unexpected behaviour.

It sounds painful and time-consuming, and it is. But avoid the temptation to
short-circuit it by republishing the image under the same tag (like
`latest`): your Job's results might change, or the Job might break, and at
the very least you introduce doubt about the reproducibility of results.

**If you change the implementation: change the container tag, then change
the Job versions.**

## What happens to earlier Job Definition versions?

When Job Definitions are re-loaded (via their manifests, using
`/admin/job-manifest/load`) the Data Manager replaces any existing
definition whose `collection`, `job` and `version` already exist. If the
version has changed the DM creates a **new** Job record, preserving the old
one.

Consequently, if you ran Job **X** version **1.0.0** yesterday you should be
able to run Job **X** version **1.0.0** today, even though version
**1.0.1** may have been loaded since.

This is also why Jobs are not removed once loaded. An **Instance** — the Pod
and model record produced by running a Job — holds a foreign key to the Job
record, and re-running an Instance requires that record to still exist. The
DM enforces this: once installed, Jobs cannot normally be removed.

## Never

- Remove Job Definition repositories that are in circulation (i.e. used in
  any Data Manager installation)
- Remove container images that are in circulation
- Change repository names or manifest filenames once Jobs are in circulation
- Move a software (Git) tag in a Job Definition repository
- Reuse a container tag

## How the Data Manager treats image tags

The DM treats the tags `latest` and `stable` as **dynamic** image content, and
ensures a new image is pulled before a Job executes (using an appropriate
Kubernetes `imagePullPolicy`).

Any other tag — like `1.0.0` — is treated as **static**: it will *not* be
re-pulled on a node that believes it already has the image. Images are cached
per Kubernetes node, so a rebuilt `1.0.0` would only be used on nodes that had
never pulled it. Some nodes would run the old content and some the new, which
is a confusing failure to debug — another reason never to reuse a tag.

Note what this means for reproducibility: a dynamic tag is *designed* to
change underneath you. It is a development convenience, not a stability
guarantee, and pinning one does not make a Job repeatable.

## Using `latest` and `stable` during development

To avoid the ceremony of semantic image tags while a Job is still moving, you
can adopt a **`latest`/`stable`** tagging strategy.

During development you rebuild and publish a new `latest` image every time you
change the implementation. Because the DM re-pulls dynamic tags, you do not
have to change Job versions while iterating — which is the whole point.

When the Job is ready for release, change the Job's `version` and publish a
new image with the `stable` tag. You are declaring that `latest` is genuinely
the latest (probably unstable) code, while `stable` represents tested,
significant changes you are happy for others to use.

The trade-off is explicit: you gain iteration speed and lose reproducibility.
Every Job pinning a dynamic tag will change behaviour whenever that tag is
republished, with no Job version change to signal it and nothing for a user to
observe.

`squonk2-jaqpot`'s `main` branch is an example of a repository working this
way today.

## A conformant example

`squonk2-jaqpot` at repository tag `1.0.4` has all three static elements in
place at once, and is deployed:

```
URL: https://raw.githubusercontent.com/InformaticsMatters/squonk2-jaqpot/1.0.4/data-manager/manifest.yaml
```

```yaml
    version: '1.1.0'
    image:
      name: informaticsmatters/squonk2-jaqpot
      tag: '1.0.4'
```

The manifest is loaded from a repository **tag**, the Job **`version`** at
that tag is fixed, and the **image tag** is static (and published —
`informaticsmatters/squonk2-jaqpot:1.0.4` exists on Docker Hub). Reloading
that manifest a year from now produces the same Job, running the same code.

## Production and development modes

> [!NOTE]
> **Proposed — under discussion in
> [#43](https://github.com/InformaticsMatters/squonk2-jobs/issues/43).**
> Not yet ratified. The rest of this page describes settled behaviour; this
> section does not. Ask a maintainer before relying on it.

The proposal is that a Job repository operates in one of two modes.

**Development mode** — for a new set of Jobs that are getting up and running
and changing frequently. Job Definitions use `latest` image tags, and the Data
Manager installation runs in `DEVELOPMENT` mode, where administrators can
adjust or remove Job Definitions on the understanding that they know the
implications.

**Stable mode** — for an established set of Jobs that need to be properly
versioned. The repository is tagged (e.g. `1.2.3`), the container images are
built and published with that tag, and the Job Definitions pin it. When a
change is made to a single Job, a new repository tag (`1.2.4`) is created, the
impacted images are rebuilt and tagged, and the impacted Job Definitions are
updated to use the new image tag.

Under the proposal:

- Production Job Definitions **must not** pin `latest` or `stable`.
- Manifests should be loaded from a repository **tag**, not a branch — a
  branch such as `main` is not a fixed point, so definitions loaded from one
  change under deployed installations on every reload.

Not every image is under our control. `3dechem/silicos-it`, for example, can
never conform to this pattern. How to handle third-party images — pinning a
digest, mirroring into our own namespace, or accepting `latest` — is one of
the open questions in #43.
