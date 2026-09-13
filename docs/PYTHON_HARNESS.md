# Python coding harness

`examples/python_harness.py` is the handoff between ClockRouter and a coding
agent or test harness. It uses the normal OpenAI Python SDK, but its `base_url`
points at ClockRouter and its model is the stable virtual name `clock/local`.
The caller never needs the upstream provider or physical model identifier.

Set a generated gateway token in the environment, start ClockRouter on the
loopback interface, and run the example:

```bash
export CLOCKROUTER_API_TOKEN='<local gateway token>'
uv run python examples/python_harness.py \
  --base-url http://127.0.0.1:4000/v1 \
  'Write a Python function that validates a UUID'
```

As a class:

```python
from examples.python_harness import ClockRouterHarness

with ClockRouterHarness() as harness:
    code = harness.prompt_code("Write a Python function that validates a UUID")
    trace = harness.last_trace
```

`prompt_code()` returns only assistant text. `last_trace` retains the
non-sensitive request ID, selected ClockRouter route, and gateway latency for
diagnostics. It never contains the prompt, response, or credential.
