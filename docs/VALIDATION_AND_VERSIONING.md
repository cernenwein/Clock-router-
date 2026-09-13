# Validation and version preservation

ClockRouter uses three independent layers. Local hooks provide fast feedback;
GitHub CI provides the durable independent result; Git commits and annotated
tags preserve exact known-good states.

## One-time installation

Install `uv`, clone the repository, then run:

```bash
bash scripts/install-hooks.sh
```

The installer synchronizes locked development dependencies, installs both Git
hooks, and executes each hook once. Hook installation is per clone because the
`.git` directory is intentionally not shared through GitHub.

## What runs

### Before `git commit`

- `ruff format --check .`
- `ruff check .`
- `uv lock --check`
- `git diff --check --cached`

These checks are deterministic and normally finish quickly. They do not modify
files automatically; a failed check leaves the staged change intact for repair.

### Before `git push`

- `uv lock --check`
- `pytest -n ${CLOCKROUTER_TEST_WORKERS:-2}`

Two workers avoid excessive process-startup overhead on the small local suite.
Set `CLOCKROUTER_TEST_WORKERS=auto` to use all available workers.

### In GitHub Actions

CI installs exactly `uv.lock`, checks Ruff formatting and lint, and then runs
`scripts/check-push.sh` with automatic worker selection. This executes the same
lock and test gate used locally. GitHub is authoritative because local hooks can
be skipped or modified.

## Push paths

All changes use the same branch-first contract:

| Path | Local gate | Remote gate | Expected action |
|---|---|---|---|
| Developer push | `scripts/check-push.sh` | Branch CI | Repair failures, then push |
| Automated/agent change | Review branch | Branch CI and PR CI | Never force or write directly to `main` |
| Pull request | Optional local rerun | Required CI | Merge only after green checks |
| Emergency hook bypass | Documented exception | Required CI | Repair tooling; do not merge broken code |

A failed local hook is a validation result, not a Git transport failure. Run
`bash scripts/check-push.sh` directly for the same diagnostic output. Review
branches are the supported solution when a direct default-branch write is
refused by an automation safety boundary; do not weaken that boundary.

## Daily feature workflow

```bash
git switch -c feature/001-gateway-hardening
# edit code, spec, and tests
git add <intentional-files>
git commit -m "Validate gateway configuration"
git push -u origin feature/001-gateway-hardening
```

Open a pull request and merge only after CI passes. Keep commits small enough to
review and revert independently. Never use a commit as evidence merely because
the local hook passed; record the acceptance commands in the active spec.

## Preserving a known-good version

After the target commit passes CI:

```bash
git switch main
git pull --ff-only
git tag -a v0.1.0 -m "ClockRouter v0.1.0 local-routing baseline"
git push origin v0.1.0
```

An annotated tag names one immutable commit. A later GitHub release may add
notes or build artifacts without replacing Git history. Never move or reuse a
published version tag; create a new version.

## Emergency bypass

Git permits `SKIP=hook-id git commit` through pre-commit and also provides
`--no-verify`. A bypass may be needed when repairing the validation tooling,
but it is not approval to merge broken code. Document the reason in the commit
or pull request and rely on GitHub CI before merging.

Examples:

```bash
SKIP=clockrouter-format git commit -m "Repair formatter configuration"
git commit --no-verify -m "Repair broken hook bootstrap"
```

## Lockfile transaction strategy

Treat a lockfile update as a transaction: the manifest, lockfile, validation
evidence, and review branch must describe one intentional dependency state.

### Version-only changes

For a ClockRouter release that does not intentionally change dependencies:

1. Start from a clean checkout of the target branch with its existing
   `pyproject.toml` and `uv.lock`. Never regenerate from a reconstructed or
   partial project.
2. Record `uv --version`. Use the repository-approved uv version; changing the
   resolver or lockfile serializer belongs in a separate tooling change.
3. Change only ClockRouter's version in `pyproject.toml`.
4. Run `uv lock` without `--upgrade`. Prefer `uv lock --offline` when the
   required package metadata is already cached.
5. Inspect `git diff -- pyproject.toml uv.lock`. The lockfile should normally
   change only ClockRouter's editable package entry. New package versions,
   hashes, wheel lists, sources, or resolution markers are unrelated churn.
6. Run `uv lock --check` and the full validation suite.
7. Push to a review branch and merge only after CI passes.

If unrelated lockfile churn appears, stop. Restore both files from the target
branch, install the approved uv version, and repeat from the complete checkout.
Do not hand-edit hashes, truncate a fetched lockfile, or accept a large diff
merely because resolution succeeds.

### Dependency changes

Make dependency changes separately from a version-only release. State the
intended packages and permitted version movement before running uv:

```bash
uv lock --upgrade-package <package>
uv sync --locked --dev
make validate
```

Review direct and transitive changes, package sources, hashes, platform wheels,
and license or security implications. Broad `uv lock --upgrade` changes require
an explicit dependency-refresh task and should not be hidden inside feature,
documentation, or release commits.

### Recovery and atomicity

Keep the original branch commit as the rollback point. Build the candidate
commit on a review branch, recheck that its parent is still the intended target,
and never force-update `main`. If validation or review fails, abandon or repair
the review branch; do not partially apply the manifest and lockfile as separate
commits.

## Useful commands

```bash
make format-check
make lint
make test
make test-parallel
make validate
make install-hooks

uv run pre-commit run --all-files
uv run pre-commit run --hook-stage pre-push --all-files
```

## Cost and trust model

Local checks cost nothing beyond local compute. GitHub-hosted CI consumes the
repository owner's included Actions allowance for a private repository.
Self-hosting on LittleMac is unnecessary at this scale and would let pull-request
code execute inside the private network. Reconsider only if hosted usage exceeds
the allowance and the runner can be isolated safely.
