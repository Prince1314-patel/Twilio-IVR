---
description: How to run the LiveKit agent locally and test with LiveKit Cloud
---

# Testing LiveKit Agent with LiveKit Cloud

This workflow describes how to run the agent locally but connect it to your LiveKit Cloud project, and test it using the LiveKit Agents Playground.

## Prerequisites

- `backend/.env` must contain `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.
- Dependencies installed: `pip install -r backend/requirements.txt`

## Step 1: Start the Agent Worker

Run the agent in development mode. It will connect to LiveKit Cloud as a worker and listen for new room sessions.

```bash
cd backend
python -m app.livekit.agent_worker dev
```

## Step 2: Generate a Test Token

You need a token to connect your browser (the "client") to the same LiveKit room as the agent. run the helper script:

```bash
# From project root
python3 scripts/generate_dev_token.py
```

This will output a `Token` and the `URL`.

## Step 3: Connect via Playground

1. Open [LiveKit Agents Playground](https://agents-playground.livekit.io/).
2. Click **Settings** (gear icon) or **Connect**.
3. Telemetry/Configuration:
   - **LiveKit Server URL**: (Paste the URL from Step 2)
   - **Token**: (Paste the Token from Step 2)
4. Click **Connect**.

## Step 4: Interact

- Ensure your microphone is enabled in the browser.
- Speak to the agent using the microphone.
- The agent should respond.
