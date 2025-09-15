# Warm Transfer MVP

A minimal warm transfer demo with FastAPI backend, Next.js frontend, LiveKit for realtime audio rooms, and Groq/OpenAI-based summary.

## Tech Stack
- Backend: FastAPI (Python) + LiveKit Server SDK + Groq/OpenAI SDKs
- Frontend: Next.js (TypeScript) + TailwindCSS + LiveKit Client/React
- Storage: In-memory Python dict for transcripts/summaries
- LLM: Groq (primary, `llama-3.1-8b-instant`) with fallback to OpenAI `gpt-4o-mini`, then dummy

## File Structure
```
/warm-transfer
  /backend
    main.py
    models.py
    requirements.txt
    /services
      livekit_client.py
      llm_client.py
      transcripts.py
  /frontend
    package.json
    tailwind.config.js
    /pages/index.tsx
    /pages/agent-a.tsx
    /pages/agent-b.tsx
    /utils/api.ts
  README.md
```

## Environment Variables
Set these in your environment or `.env` (backend) and `.env.local` (frontend):

Backend (.env):
- `LIVEKIT_API_KEY` (required)
- `LIVEKIT_API_SECRET` (required)
- `LIVEKIT_URL` (e.g. `https://your-livekit-host`) — used by clients
- `GROQ_API_KEY` (optional, preferred if set)
- `OPENAI_API_KEY` (optional, secondary fallback)
- `CALLER_IDENTITY` (optional, default `caller`)

Frontend (.env.local):
- `NEXT_PUBLIC_BACKEND_URL` (default `http://localhost:8000`)
- `NEXT_PUBLIC_LIVEKIT_URL` (e.g. `wss://your-livekit-host`) — Websocket URL

## Backend Setup
```
cd warm-transfer/backend
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup
```
cd warm-transfer/frontend
npm install
npm run dev
```
Visit `http://localhost:3000`.

## Warm Transfer Workflow
1. Caller visits `/` and clicks Join → backend creates `roomA`, returns token, Caller connects.
2. Agent A visits `/agent-a` and clicks Join → joins `roomA`, types notes during call.
3. Agent A clicks Transfer → backend creates `roomB`, generates a summary via Groq/OpenAI from transcript, returns tokens for initiator (Agent A), target (Agent B), and Caller. Agent A broadcasts a warm transfer message in room A.
4. Caller auto-joins `roomB` using the received `caller_token`.
5. Agent A auto-joins `roomB` with the initiator token and sees the summary to read to Agent B.
6. Agent B visits `/agent-b`, enters `roomB` name, clicks Join → fetches and displays the summary.
7. Agent A may leave; Caller and Agent B remain connected in `roomB`.

## Notes
- Transcript and summary are in-memory; restart clears data.
- If neither `GROQ_API_KEY` nor `OPENAI_API_KEY` is set, a dummy summary is returned.
- Ensure your LiveKit host is reachable from the browser and tokens are minted with matching `room`.
