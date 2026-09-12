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

- `pytest -n 2`

Two workers avoid excessive process-startup overhead on the small local suite.
Developers may choose more workers manually with `pytest -n auto`.

### In GitHub Actions

CI installs exactly `uv.lock`, checks Ruff formatting and lint, and runs the
parallel test suite. GitHub is the authoritative result because local hooks can
be skipped or modified.

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
