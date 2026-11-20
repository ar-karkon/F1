# SovInfra provider setup — AI Race Engineer (Apex Intelligence)

**Verified against public SovInfra provider documentation on 2026-11-20.**

| Setting | Value |
| --- | --- |
| API base URL | `https://api.sovinfra.ai/v1` |
| Endpoint used | `POST /chat/completions` |
| Default automatic routing | `sovapi` |
| Direct code/reasoning model | `qwen3.8-27b` |
| Direct general/vision model | `gemma-4-31b` |
| Contract | OpenAI-compatible Chat Completions |

Official sources: https://arena.sovinfra.ai/ and https://sovinfra.ai/

## Critical security advice

If an API key was pasted into a chat, screenshot, repository, log or ticket,
**revoke that exact key and generate a new one** in the SovInfra console.
Never share the replacement key with this chat. Apex intentionally stores
no real credentials. The tracked example env file contains no keys.

## Linux / macOS

Run from an updated F1 checkout:

```bash
git pull
python -m pip install -e ".[dev]"

# Obtain an unexposed NEW key from SovInfra first.
# Key input is hidden and not typed into shell history:
read -rsp "New SovInfra API key: " SOVINFRA_API_KEY; echo
export SOVINFRA_API_KEY
export APEX_LLM_ENABLED=true
export APEX_LLM_BASE_URL=https://api.sovinfra.ai/v1
export APEX_LLM_MODEL=sovapi

# Explicit test, sends a generic prompt and NO racing data:
apex-f1 llm-smoke

# Research-only historic race (OpenF1, no LLM involved):
apex-f1 import-race --year 2024 --round 1 --provider openf1
apex-f1 serve
```

Open `http://localhost:8000/replay`, choose a lap, click
**Generate historical brief**. Only this explicit click sends the selected
historical snapshot to SovInfra, consuming API tokens.

## Windows PowerShell

```powershell
git pull
python -m pip install -e ".[dev]"
$secret = Read-Host "New SovInfra API key" -AsSecureString
$env:SOVINFRA_API_KEY = [System.Net.NetworkCredential]::new("", $secret).Password
$env:APEX_LLM_ENABLED = "true"
$env:APEX_LLM_MODEL = "sovapi"
$env:APEX_LLM_BASE_URL = "https://api.sovinfra.ai/v1"
apex-f1 llm-smoke
apex-f1 import-race --year 2024 --round 1 --provider openf1
apex-f1 serve
```

## Model selection

Prefer `sovapi` automatic routing initially. Override
`APEX_LLM_MODEL` with `qwen3.8-27b` or `gemma-4-31b`
for later model comparisons. Both are unvalidated for motorsport
strategy: this integration generates historical commentary only.

## Troubleshooting

- **`configured: false`**: enable `APEX_LLM_ENABLED` and export a key
  into the same environment as the server.
- **Authentication failure**: replace the key, inspect permissions, or
  check account status. Apex intentionally suppresses raw provider error
  bodies (which may contain sensitive metadata).
- **Schema/model error**: ensure the account supports `/chat/completions`,
  the chosen model name, and the OpenAI-style `temperature`/`max_tokens` fields.
- **Invalid AI brief JSON**: smoke test may succeed but the model's analysis
  may not match the evidence-linked output contract. This is not reported as
  success or silently repaired with invented data.
- **No race data**: run the explicit OpenF1 import before replaying.
- GitHub Actions CI uses mocked HTTP; it **does not use your private key**.

## Privacy, licensing and access controls

OpenF1 historical source usage is subject to non-commercial and other
data-use conditions. External LLM processing should be evaluated under
separate provider privacy/retention terms. The Apex API does not implement
logins or rate limits. Only bind it to `127.0.0.1` in this stage; do
not expose a server with an enabled API key to the public internet.
