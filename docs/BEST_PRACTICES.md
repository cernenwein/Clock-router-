# Best practices and primary references

Last reviewed: 2026-09-12

This is a curated engineering guide, not a link dump. Each source is official or
maintained by the relevant project, and each entry records how ClockRouter uses
it. Re-check sources when a spec changes the associated subsystem.

## Spec-driven and agent-assisted development

### GitHub Spec Kit

- [Spec Kit repository](https://github.com/github/spec-kit)
- [Spec Kit documentation](https://github.github.io/spec-kit/)
- [GitHub's introduction to spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)

ClockRouter adopts the durable progression of constitution → specification →
plan → tasks → implementation. It intentionally uses a smaller, repository-local
version rather than adding a framework dependency. Specifications state desired
behavior and acceptance criteria; plans state implementation choices.

### Agent instructions

- [OpenAI: custom instructions with `AGENTS.md`](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [`AGENTS.md` open format](https://agents.md/)
- [GitHub: repository custom instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)

ClockRouter keeps its tool-independent contract in root `AGENTS.md`. The small
`.github/copilot-instructions.md` points GitHub-hosted agents to the same source
of truth instead of maintaining two divergent rule sets.

## API and Python service engineering

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/)
- [HTTPX async support](https://www.python-httpx.org/async/)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)

ClockRouter uses one lifespan-managed HTTP client, explicit timeouts, startup
configuration validation, typed settings, and tests at both pure-policy and API
contract boundaries. Streaming tests must prove upstream resources close on
normal completion, client cancellation, and upstream error.

## OpenAI-compatible interfaces

- [OpenAI Chat Completions API reference](https://platform.openai.com/docs/api-reference/chat)
- [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses)
- [LM Studio OpenAI compatibility](https://lmstudio.ai/docs/developer/openai-compat)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)

Compatibility is a testable contract. A provider calling itself compatible is
not sufficient evidence. Specs that add or change endpoints identify supported
fields, streaming behavior, error mapping, tool calls, and deliberate omissions.

## AI and application security

- [OWASP Top 10 for LLM applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OWASP prompt-injection prevention cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [GitHub secret-scanning documentation](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning)
- [GitHub dependency security documentation](https://docs.github.com/en/code-security/dependabot)

ClockRouter treats model input and output as untrusted data. Neither may alter
routing policy, authorize cloud use, reveal credentials, or become executable
instructions without a separately authorized controller. Access decisions are
server-side, deny by default, and tested with negative cases. Secrets come from
the environment and are excluded from logs and version control.

## Logging and observability

- [OWASP logging cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OpenTelemetry semantic conventions for HTTP](https://opentelemetry.io/docs/specs/semconv/http/)

Log request IDs, route decisions, token counts, cost, latency, and status. Do not
log prompts, completions, authorization headers, API keys, or raw upstream error
bodies that may echo user content. Telemetry schemas require a privacy review.

## Containers and supply chain

- [Dockerfile best practices](https://docs.docker.com/build/building/best-practices/)
- [Docker Compose production guidance](https://docs.docker.com/compose/how-tos/production/)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [Python Packaging User Guide: dependency specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)

Use small trusted base images, pinned dependency ranges and lock files, minimal
container privileges, read-only configuration mounts, and localhost/private
overlay exposure by default. CI permissions stay read-only unless a specific
job demonstrably requires more.

## Pull-request checklist for linked guidance

- Does the active spec cite the relevant section above?
- Are new external recommendations primary sources where possible?
- Are claims translated into ClockRouter-specific requirements and tests?
- Has the source review date been updated when behavior depends on current docs?
- Are privacy, denial, cancellation, timeout, and cost-limit paths tested?
