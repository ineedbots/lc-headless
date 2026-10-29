# Development Workflow

Feature work flows through `develop`. Published releases come from tagged commits on `master`.
This document defines the repository policy; branch protection and automated enforcement must be configured
separately in the repository settings and workflows.

## Branches

| Branch | Purpose | How it changes |
|---|---|---|
| `master` | Source for published, tagged releases | Fast-forward to a release-ready commit from `develop` |
| `develop` | Integration branch for the next release | Reviewed feature branch pull requests with passing CI |
| Feature branches | Features, fixes, tests, documentation and maintenance | Branch from `develop`, then open a pull request into `develop` |

Protect both `master` and `develop` against deletion and force pushes. Require the CI build and coverage checks
before accepting changes. Require reviewed pull requests into `develop`, with checks passing against the current
integration branch. Restrict updates to `master` to release maintainers following the promotion procedure below.
Routine feature work and release fixes go through `develop`, including version changes; do not commit directly
to `master`.

Use descriptive feature branch names, such as `feature/prayer-support`, `fix/quest-recovery` or
`docs/development-workflow`. Keep each pull request focused and describe its behavior and validation.
If a pull request is squash-merged, its final squash commit must follow the commit message convention below.

## CI and release policy

The [CI workflow](../../.github/workflows/ci.yml) runs on pull requests and pushes to both `develop` and `master`.
All required checks must pass on the selected release commit before promotion.

The [release workflow](../../.github/workflows/release.yml) runs when a `v*` tag is pushed. The numeric version
must match `project(... VERSION ...)` in `CMakeLists.txt`. A suffix such as `-rc1` marks a prerelease.
Release tags must point to the promoted commit on `master`; never tag a feature branch or an unpromoted
`develop` commit for publication. Published tags must not be moved or reused.

The current release workflow checks the version and builds, tests and publishes the packages. It does not
check that the tagged commit is on `master`; release maintainers must enforce that policy until an automated
guard is added. This document does not itself enable branch or tag protection.

## Promoting a release

1. Merge all release changes, including the project version, into `develop` through pull requests.
2. Select the release-ready `develop` commit and wait for all of its required CI checks to pass. Record its full
   commit SHA so later changes to `develop` cannot change the release selection.
3. From a clean working tree, fetch the remote branches and fast-forward `master` to that exact SHA. The
   previous `master` commit must be an ancestor of the selected commit. If it is not, stop and reconcile the
   history through `develop`; do not force-push or create a release-only merge commit.
4. Push `master` through the authorized release maintainer path. Confirm CI passes on the promoted commit.
5. Create an annotated version tag on that same SHA and push the tag to trigger publication. Verify the
   release workflow succeeds and the expected packages are published.

For example, with `RELEASE_SHA` replaced by the selected full SHA and `vX.Y.Z` replaced by the matching version:

```sh
git fetch origin
git switch master
git merge --ff-only origin/master
git merge --ff-only RELEASE_SHA
git push origin master
# After CI succeeds on the promoted commit:
git tag -a vX.Y.Z RELEASE_SHA -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Verify the selected SHA belongs to `origin/develop` and that local `master` matches `origin/master` before
starting the promotion. These commands assume the maintainer has permission to promote the protected branch.
Configure that permission narrowly. A promotion must preserve the selected commit SHA: a squash merge,
rebased copy or additional merge commit would create a different release commit.

If a published release needs a fix, make the fix through a feature branch and `develop`, then promote and tag
a new release using the same procedure.

## Commit messages

Use a Conventional Commits-style message with a required scope:

```text
type(scope): description
```

This is the `thing(noun): description` pattern: `type` names the kind of change and `scope` names the affected
subsystem or area. Both are lowercase. Use `feat` for features, rather than `feature`.
The description states the change in the imperative, starts with a lowercase word and has no trailing period.
Keep the subject concise and specific. Include the scope for every authored commit, including documentation
and CI changes.

| Type | Use |
|---|---|
| `feat` | Add a capability |
| `fix` | Correct a bug |
| `refactor` | Restructure code while preserving externally observable behavior |
| `test` | Add or change tests |
| `docs` | Add or change documentation |
| `ci` | Change continuous integration or release automation |
| `build` | Change build configuration, dependencies or packaging |
| `perf` | Improve performance |
| `style` | Change formatting without changing behavior |
| `chore` | Other repository maintenance |

Use scopes such as `stdlib`, `config`, `protocol`, `navigation`, `coverage`, `workflow` or `release`.
Prefer an existing scope when it fits. Choose the type for the primary purpose of the change: use `perf` when
the purpose is a performance improvement, and `refactor` when the purpose is restructuring. A refactor may
also improve performance. Substantiate specific complexity or timing claims in the body; replacing a loop
with a join alone does not establish a particular complexity bound.

### Subject-only commits

A subject is enough for a straightforward change:

```text
feat(ui): add dark mode toggle switch
```

Repository examples:

```text
feat(config): add an option to disable the script watchdog
fix(stdlib): recover prayer quests after interrupted dialogue
test(stdlib): cover shared quest edge workflows
ci(workflow): run checks on develop pushes
docs(workflow): document branch promotion and commit messages
build(release): bump the project version to 0.2.0
```

### Bodies and issue references

For a change that needs explanation, separate the subject from the body with a blank line. Explain what
changed, why it changed and any relevant tradeoffs or validation. Normal sentence capitalization and
punctuation belong in the body. Wrap long prose lines at about 80 characters.

Place issue references in a footer, separated from the body by a blank line. Use `Resolves: #8421` when the
commit resolves that issue, or `Refs: #8421` when it only relates to it. For example:

```text
refactor(database): simplify query profiling for user profiles

Replaced the nested loop query logic with an explicit inner join.
This keeps profile selection in the database and simplifies the dashboard
load workflow while preserving the returned profiles.

Resolves: #8421
```

This example documents the restructuring without asserting an unverified performance bound. If performance
is the main change, use a subject such as `perf(database): reduce profile query time` and include measurements
and their conditions in the body.

### Breaking changes

For an incompatible change, put `!` immediately after the scope and before the colon. Also include a
`BREAKING CHANGE:` footer explaining what is no longer supported and what callers must do to migrate.
Use both markers so the subject signals the incompatibility and the footer provides actionable details.
Any change type can be breaking; `!` is not limited to `feat`.

```text
feat(payments)!: transition from Stripe v2 to v3 SDK

BREAKING CHANGE: The older charge payload contract is no longer supported.
All payment integrations must now transition to the new PaymentIntent
object standard.
```

The payment example illustrates the message format; it does not describe a repository dependency.
For this project, breaking changes include incompatible script API, configuration or protocol contract
changes. Explain the migration even when the implementation change is small.

Keep unrelated changes in separate commits. Apply the same format to the final commit produced by a squash
merge, preserving any issue references and breaking change details. These rules apply to new commits;
existing history does not need rewriting to adopt them. The message convention does not itself bump versions
or publish releases; follow the release procedure above.
