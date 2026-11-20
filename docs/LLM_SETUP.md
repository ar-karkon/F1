# Optional AI Race Engineer: bring your own LLM API

## Scope

The OpenAI-compatible `/chat/completions` adapter provides **historical
commentary only** for a selected lap in the local replay UI. It is NOT a
strategy optimizer, validated predictor, safe real-time engineer, or the
F1-StratLab no-LLM pipeline. No inference runs unless explicitly requested.

The LLM feature is **disabled by default**. It reads environment variables
when handling API calls and never stores an API key in the repository or in
a response.

## Setup (Linux / macOS)

```bash
git pull
python -m pip install -e ".[dev]"

# Historic OpenF1 data, no API key needed:
apex-f1 import-race --year 2024 --round 1 --provider openf1

# Only put your actual key in your PRIVATE shell environment:
export APEX_LLM_ENABLED=true
export APEX_LLM_API_KEY="YOUR_PRIVATE_KEY"
export APEX_LLM_MODEL="MODEL_ID_SUPPORTED_BY_YOUR_PROVIDER"
export APEX_LLM_BASE_URL="https://YOUR_PROVIDER_HOST/v1"

apex-f1 serve
```

PowerShell:

```powershell
$env:APEX_LLM_ENABLED="true"
$env:APEX_LLM_API_KEY="YOUR_PRIVATE_KEY"
$env:APEX_LLM_MODEL="MODEL_ID_SUPPORTED_BY_YOUR_PROVIDER"
$env:APEX_LLM_BASE_URL="https://YOUR_PROVIDER_HOST/v1"
apex-f1 serve
```

Replace the model ID and base URL with values from **your actual provider's
documentation**. Do not point the API at a web-chat URL. The endpoint must
support `POST {BASE_URL}/chat/completions` and standard
`choices[0].message.content` responses. LLM output is requested as JSON.
Some OpenAI-style services may require a different schema; adapt in a
separate tested provider module rather than guessing.

Open `http://localhost:8000/replay`. If the model reports configured,
choose a historical lap and explicitly click **Generate historical brief**.
The UI shows linked evidence IDs, observations and known unknowns.

The app does not automatically load a local `.env` file; supply actual
environment variables before launching. The `.env.example` file contains
configuration **placeholders only**.

## API

- `GET /api/v1/llm/status` → whether configured; never returns key or full base URL.
- `POST /api/v1/historical/2024/1/brief/17` →
  `{"focus":"overview"}`, optional focus `tyres`, `pit_activity` or
  `rivals`.

Model response includes `brief`, up to 4 `observations` with
`D_<DRIVER_CODE>` evidence references, a list of uncertainties and a
clear unvalidated-research status. Invalid structure or unknown evidence
IDs result in HTTP 502, never fabricated fallback commentary.

## Security and privacy

- The **local web server does not have authentication or rate limits**:
  bind to `127.0.0.1` only; DO NOT expose to a public network as-is.
- Enabling this feature will send the selected **OpenF1/FastF1 historical
  snapshot** to your external LLM provider when you click Generate.
  Check the source's commercial-use rights and your provider's policies on
  retention and model training first.
- No full-session data, future laps, secret, or live information is
  intentionally sent by the adapter. Upstream historical sources may
  include retrospective corrections; field disclosure timing is not proven.
- The model's output is checked for JSON shape and evidence references,
  **not independently verified for factual truth**. Never use the output
  for pit-wall operations, safety-critical choices or claims of accuracy.
- Only HTTPS endpoints are allowed except loopback localhost for local
  development. Configuration and provider error details are not echoed.
- No real LLM request occurs in CI; offline tests mock HTTP requests and
  verify future-lap separation.

## Next engineering gate

To progress beyond historical explanation: validate F1-StratLab
`no-llm` against legitimate race data in its separate runtime, build a
chronological pit-decision baseline, and compare it with the LLM's
non-predictive commentary. LLM text is **not** a substitute for quantitative
simulation or opponent behavior models.
