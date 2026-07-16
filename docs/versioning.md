# Versioning Jobs

To use Jobs in a safe and repeatable way you need to version them. Two
version values are involved:

- the Job's **`version`** in its Job Definition, and
- the **tag** of the container image that contains its implementation.

When you reach a point of stability with your Job you should protect your
work by versioning it. A strict versioning policy will inevitably slow down
your development throughput, but without it you risk not being able to
re-run valuable experiments — or, worse, breaking or silently altering the
behaviour of Jobs already in circulation.

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

## Never

- Remove Job Definition repositories that are in circulation (i.e. used in
  any Data Manager installation)
- Remove container images that are in circulation
- Change repository names or manifest filenames once Jobs are in circulation
- Move a software (Git) tag in a Job Definition repository
- Reuse a container tag

## If you have to use `latest` image tags

To avoid the ceremony of semantic image tags during development you can
adopt a **`latest`/`stable`** tagging strategy, paired with separate
branches for the corresponding *manifests*.

During development you rebuild and publish a new `latest` image every time
you change the implementation. As long as you understand the risk, that is
fine: the Data Manager treats the tags `latest` and `stable` as **dynamic**
image content and ensures any new image is pulled before a Job executes
(using an appropriate Kubernetes `imagePullPolicy`), so you do not have to
change Job versions while iterating.

Any other tag — like `1.0.0` — is treated as **static**: it will *not* be
re-pulled on a node that believes it already has the image. (Images are
cached per Kubernetes node, so a rebuilt `1.0.0` would only be used on nodes
that have never pulled it — another reason never to reuse a tag.)

When the Job is ready for release, change the Job's `version` and publish a
new image with the `stable` tag. You are declaring that `latest` is
genuinely the latest (probably unstable) code, while `stable` represents
tested, significant changes you are happy for others to use.

The manifest you deploy to a *development* environment refers to Job
Definitions using `latest` image tags; the manifest for a *production*
environment refers to definitions using `stable` tags. You cannot deploy
both manifests to the same environment if the Job versions are the same.

Our [virtual-screening](https://github.com/InformaticsMatters/virtual-screening)
repository uses this pattern: pushes to `main` publish `:stable` images and
pushes to `staging` publish `:latest`.
