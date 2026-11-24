# AEGIS — Assisted Executive Guidance and Intelligence System

**Smart India Hackathon 2026 · PS SIH26202 / SIH26204 · Team Code Kendra**
*"Tell AEGIS what you want. AEGIS determines how to get it done."*

A voice-first, accessibility-first desktop AI agent for Windows 10/11 that **sees**, **hears**, **knows**, **acts** and **remembers**.

## Architecture

```
INPUT  ──▶ UNDERSTAND ──▶ ROUTE ──▶ REASON ──▶ ACT ──▶ MEMORY
Mic /      Faster-Whisper  Deterministic  Gemini 2.5 Flash   Win32 / Browser /   SQLite +
Camera /   YOLOv5m ONNX    router <5 ms   (ReAct) + free     Media / Reminders / Spatial episodic
Chat                                      web search         Hardware            memory
```

| Layer | Implementation |
|---|---|
| Backend | FastAPI + Uvicorn, WebSocket event bus (`backend/main.py`) |
| Frontend | React 18 + TypeScript + Vite + Tailwind (`frontend/`, prebuilt in `frontend/dist`) |
| Router | Regex deterministic router for frequent commands (`backend/agent/router.py`) |
| Agent | `AegisAgent` ReAct loop on **Gemini 2.5 Flash** with native tool-calling over 30 registered tools; OpenRouter and fully-offline fallbacks (`backend/agent/llm_agent.py`) |
| Vision | YOLOv5m via ONNX Runtime; **EMA smoothing + 850 ms persistence** tracker (`backend/services/tracker.py`); YOLOX-tiny fallback |
| Spatial memory | Stable targets → category, relation, room, timestamp in SQLite. **No raw video is stored.** |
| Voice | Faster-Whisper STT, Edge-TTS (pyttsx3 offline fallback), instant barge-in |
| Memory / reminders | SQLite + SQLAlchemy, APScheduler, `dateparser` |
| Auth | Google Sign-In (OAuth token verified server-side) with local-profile fallback (`backend/auth.py`) |
| Accessibility | Voice-first, barge-in, high contrast, OpenDyslexic, reduced motion, text scaling, keyboard operable |

## Run it (Windows)

```powershell
.\start_aegis.ps1
```
Creates a venv, installs requirements, downloads the YOLOv5m weights (~42 MB, once), and opens http://127.0.0.1:8000.

Optional `.env` (copy `.env.example`): `GEMINI_API_KEY` for Gemini 2.5 Flash reasoning, `GOOGLE_CLIENT_ID` for Google Sign-In
(add `http://127.0.0.1:8000` as an Authorized JavaScript origin). With no keys AEGIS still runs: router, local vision, reminders, routines and memory all work offline.

**Voice:** hold **Space** (or the Push To Talk button). Speaking while AEGIS talks interrupts it.

### Frontend development
```powershell
cd frontend; npm install; npm run dev     # http://localhost:5173, proxies /api and /ws to :8000
npm run build                             # refresh frontend/dist
```

## Tests
```powershell
python -m pytest
```
Unit (router, math, STT normalisation, tracker EMA/persistence, YOLO decoding, reminders, routines, memory, auth tokens, Gemini ReAct with mocked HTTP) ·
Integration (REST + SQLite + auth) · E2E (real WebSocket flows: command cycle, live vision, due-reminder push, barge-in).

## Repository layout
```
backend/      FastAPI app, agent, router, tools, services (vision, tracker, memory, scheduler, STT/TTS), auth
frontend/     React 18 + TS + Vite UI (src/) and prebuilt dist/
tests/        unit / integration / e2e
scripts/      download_models.py
core/ actions/ supervision/ web/ memory/ speech/ ai/   — earlier "v2 Jarvis" Flask prototype, kept for reference; not used by the app above
```
