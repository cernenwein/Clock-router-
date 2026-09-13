# Local provider harness

The local harness verifies that LM Studio or Ollama exposes its
OpenAI-compatible model list and that ClockRouter can complete a chat request
through the configured local route. It uses a fixed, non-sensitive prompt and
prints only provider/model identifiers, ClockRouter request metadata, and
status.

## Before running

Start one provider and load or pull a model:

- LM Studio defaults to \`http://127.0.0.1:1234/v1\`.
- Ollama defaults to \`http://127.0.0.1:11434/v1\`.

Set \`config/models.yaml\` to the exact model identifier reported by the
provider. List the selected identifier without contacting ClockRouter:

\`\`\`bash
uv run python scripts/local_provider_harness.py --provider lmstudio --list-only
uv run python scripts/local_provider_harness.py --provider ollama --list-only
\`\`\`

Start ClockRouter, then run a round trip:

\`\`\`bash
export CLOCKROUTER_API_TOKEN='<local gateway token>'
uv run python scripts/local_provider_harness.py \\
  --provider lmstudio \\
  --provider-model '<loaded LM Studio model id>'

uv run python scripts/local_provider_harness.py \\
  --provider ollama \\
  --provider-model '<pulled Ollama model id>'
\`\`\`

For LittleMac over a trusted LAN or NetBird overlay, specify both URLs and opt
in to private-network access:

\`\`\`bash
uv run python scripts/local_provider_harness.py \\
  --provider lmstudio \\
  --provider-url http://192.168.0.90:1234/v1 \\
  --gateway-url http://192.168.0.90:4000 \\
  --allow-private-network
\`\`\`

The flag permits private IPs or explicitly named trusted-network hosts; public
IP literals remain denied. Do not expose either service to the public internet.

## CI boundary

CI unit-tests parsing, model selection, and network-safety rules. It never
contacts a live model, downloads weights, or sends a prompt. Live smoke tests
are opt-in because runner hardware, model availability, and local network
access are not reproducible in GitHub-hosted CI.

Official protocol references:

- https://lmstudio.ai/docs/developer/openai-compat
- https://docs.ollama.com/api/openai-compatibility
