# Local provider harness

The local harness verifies that LM Studio or Ollama exposes its
OpenAI-compatible model list and that ClockRouter can complete a chat request
through the configured local route. It uses a fixed, non-sensitive prompt and
prints only provider/model identifiers, ClockRouter request metadata, and
status.

## Before running

Start one provider and load or pull a model:

- LM Studio defaults to `http://127.0.0.1:1234/v1`.
- Ollama defaults to `http://127.0.0.1:11434/v1`.

Set `config/models.yaml` to the exact model identifier reported by the
provider. List the selected identifier without contacting ClockRouter:

```bash
uv run python scripts/local_provider_harness.py --provider lmstudio --list-only
uv run python scripts/local_provider_harness.py --provider ollama --list-only
```

Start ClockRouter, then run a round trip:

```bash
export CLOCKROUTER_API_TOKEN='<local gateway token>'
uv run python scripts/local_provider_harness.py \
  --provider lmstudio \
  --provider-model '<loaded LM Studio model id>'

uv run python scripts/local_provider_harness.py \
  --provider ollama \
  --provider-model '<pulled Ollama model id>'
```

Run both providers and the provider-agnostic Python client with one command:

```bash
uv run python scripts/live_provider_acceptance.py
```

Use `--lmstudio-model` or `--ollama-model` to select an exact loaded model. Run
this acceptance command directly on the machine hosting the providers: it
rejects non-loopback endpoints. Output contains provider labels, check names,
and status only.

## CI boundary

CI unit-tests parsing, model selection, and network-safety rules. It never
contacts a live model, downloads weights, or sends a prompt. Live smoke tests
are opt-in because runner hardware, model availability, and local network
access are not reproducible in GitHub-hosted CI.

Official protocol references:

- https://lmstudio.ai/docs/developer/openai-compat
- https://docs.ollama.com/api/openai-compatibility
