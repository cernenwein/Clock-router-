# Security policy

ClockRouter is pre-release software and has no supported production version yet.

## Reporting a vulnerability

Do not open a public issue containing credentials, prompts, personal data, or an
exploitable proof of concept. Use GitHub's private vulnerability reporting when
enabled for this repository. If it is unavailable, contact the repository owner
privately before sharing sensitive details.

Include the affected commit, impact, minimal reproduction, and suggested
mitigation. Remove real provider keys and user content from all evidence.

## Security expectations

- Treat request and model content as untrusted data.
- Deny unknown projects and unauthorized cloud routes.
- Never log secrets, prompts, completions, or authorization headers.
- Keep provider credentials only on the gateway host.
- Bind to localhost or an explicitly configured private interface by default.
- Check cloud eligibility and budgets before dispatch.
- Avoid executing model output; a separate, least-privileged controller must
  authorize tools and side effects.

See `docs/BEST_PRACTICES.md` for the project security references.
