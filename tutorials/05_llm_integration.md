# Tutorial 5 — LLM Integration

BoFire++ includes a built-in LLM client module that lets you bring language model reasoning into your optimization workflow.
The default implementation uses Google Gemini.

---

## Overview

The `llm/` package exposes:

| Symbol | Description |
|--------|-------------|
| `LLMClient` | Abstract base class — implement this to add new providers |
| `LLMMessage` | Dataclass for a single chat message (`role` + `content`) |
| `GeminiClient` | Concrete implementation backed by Google Gemini |

---

## Setup

### Option A — Replit AI Integrations (zero config)

If you are running inside Replit, the Gemini proxy is already provisioned.
Just create a client — no key needed:

```python
from llm import GeminiClient
llm = GeminiClient()
```

### Option B — Your own Gemini API key

Set the `GEMINI_API_KEY` environment variable to your key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey):

```bash
export GEMINI_API_KEY="AIza..."
```

Then:

```python
from llm import GeminiClient
llm = GeminiClient()   # picks up GEMINI_API_KEY automatically
```

### Option C — Pass the key directly in code

```python
from llm import GeminiClient
llm = GeminiClient(api_key="AIza...", model_name="gemini-2.5-pro")
```

---

## Key resolution order

`GeminiClient` resolves the API key in this priority order:

1. `api_key=` argument passed to the constructor
2. `GEMINI_API_KEY` environment variable (your key)
3. `AI_INTEGRATIONS_GEMINI_API_KEY` environment variable (Replit proxy key)

The base URL follows a similar order (`base_url=` → `AI_INTEGRATIONS_GEMINI_BASE_URL` → default Gemini endpoint).

---

## Available models

| Model | Best for |
|-------|----------|
| `gemini-2.5-flash` | Fast general-purpose — **default** |
| `gemini-2.5-pro` | Best reasoning and coding |
| `gemini-3-flash-preview` | High-volume hybrid reasoning |
| `gemini-3-pro-preview` | Agentic and complex tasks |
| `gemini-3.1-pro-preview` | Latest, most powerful |

```python
llm = GeminiClient(model_name="gemini-2.5-pro")
```

---

## `complete()` — single-turn prompt

Send a plain text prompt and get a plain text response:

```python
from llm import GeminiClient

llm = GeminiClient()
answer = llm.complete("What is Bayesian optimization? Answer in two sentences.")
print(answer)
```

---

## `chat()` — multi-turn conversation

Pass a list of `LLMMessage` objects with `role` set to `"system"`, `"user"`, or `"assistant"`:

```python
from llm import GeminiClient, LLMMessage

llm = GeminiClient()

reply = llm.chat([
    LLMMessage(role="system",    content="You are a helpful lab assistant for chemistry experiments."),
    LLMMessage(role="user",      content="Our last proposal gave yield=0.72. What should we try next?"),
])
print(reply)
```

---

## Example — Interpreting campaign results

Combine campaign data from the API with an LLM call to get a natural-language summary:

```python
import requests
from llm import GeminiClient, LLMMessage

BASE = "http://localhost:8000"
CID  = "<your-campaign-id>"

# Fetch campaign state
campaign   = requests.get(f"{BASE}/campaigns/{CID}").json()
proposals  = campaign["proposals"]
n_exp      = campaign["n_experiments"]
context    = campaign.get("context", "")

# Build a prompt
summary_prompt = f"""
Campaign context: {context}

This campaign has run {n_exp} experiments and generated these proposals:
{proposals}

Summarize what has been learned so far and suggest what region of the design space
to explore next. Be concise — 3 to 5 sentences.
"""

llm = GeminiClient()
print(llm.complete(summary_prompt))
```

---

## Example — Suggesting better feature ranges

```python
from llm import GeminiClient, LLMMessage

llm = GeminiClient()

conversation = [
    LLMMessage(
        role="system",
        content=(
            "You are an expert in process optimization. "
            "Your job is to suggest improvements to experiment designs based on observed data."
        ),
    ),
    LLMMessage(
        role="user",
        content=(
            "We are optimizing a polymerization reaction. "
            "Current inputs: temperature [80, 220]°C, time [1, 10] h, catalyst = {Cat-A, Cat-B, Cat-C}. "
            "After 12 experiments the best yield was 0.81 at temperature=195°C, time=8h, catalyst=Cat-B. "
            "Should we narrow the search space? If so, what new bounds would you suggest?"
        ),
    ),
]

advice = llm.chat(conversation)
print(advice)
```

---

## Implementing a new provider

Subclass `LLMClient` and implement `complete()` and `chat()`:

```python
from llm.base import LLMClient, LLMMessage

class MyProvider(LLMClient):
    def complete(self, prompt: str, **kwargs) -> str:
        # call your API here
        return my_api.generate(prompt)

    def chat(self, messages: list[LLMMessage], **kwargs) -> str:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        return my_api.chat(payload)

llm = MyProvider(model_name="my-model-v1")
print(llm.complete("Hello!"))
```

---

## Where to go from here

The LLM client is deliberately lightweight — a pair of methods with no framework lock-in.
Typical next steps:

- Feed campaign proposals into `chat()` and ask for interpretation
- Use `complete()` to generate a human-readable experiment report
- Build an agent loop that calls the campaign API, reads results, and asks the LLM for the next action
