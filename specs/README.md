# Feature specifications

Directories use `NNN-kebab-case-name`. Numbers are never reused. Each feature
contains:

- `spec.md`: outcomes, scope, requirements, acceptance evidence
- `plan.md`: technical design and verification strategy
- `tasks.md`: ordered implementation checklist

Create one with `bash scripts/new-spec.sh "feature-name"`. A feature may enter
implementation only when its status is `Ready` or `Active` and no unresolved
`[NEEDS DECISION]` markers remain.
