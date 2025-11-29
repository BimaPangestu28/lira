# LIRA - Real-time Voice English Speaking Agent

A real-time **voice-to-voice English speaking agent** that listens, processes, responds, and provides corrections through natural spoken interaction.

## Features

- **Real-time voice conversation** - Speak naturally, get instant voice responses
- **Multiple practice modes** - Free talk, corrective feedback, roleplay, guided practice
- **CEFR level adaptation** - Adjusts vocabulary for A2, B1, B2, C1 levels
- **Low-latency streaming** - Filler audio masks processing delay for natural feel
- **Grammar corrections** - Optional gentle corrections during conversation

## Architecture

```
User Audio (Browser)
        ↓
    LiveKit (WebRTC)
        ↓
  Deepgram STT (streaming)
        ↓
  LangGraph Agent (GPT-4o-mini)
        ↓
  Deepgram TTS (streaming)
        ↓
    LiveKit Playback → User
```

## Tech Stack

### Backend (Python 3.10+)
- **FastAPI** - REST API & WebSocket
- **LiveKit** - WebRTC audio transport
- **Deepgram** - Speech-to-text & text-to-speech
- **LangChain + LangGraph** - LLM orchestration
- **OpenAI / Azure OpenAI** - Language model

### Frontend
- **Next.js 14** - React framework
- **LiveKit Client** - WebRTC SDK
- **Tailwind CSS + shadcn/ui** - Styling

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- LiveKit server (cloud or self-hosted)
- Deepgram API key
- OpenAI API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload --port 8011
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with backend URL

# Run dev server
npm run dev
```

Open http://localhost:3000 to start practicing!

## Environment Variables

### Backend (.env)
```env
# LiveKit
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Deepgram
DEEPGRAM_API_KEY=your_deepgram_key

# LLM (choose one)
LLM_PROVIDER=openai  # or azure_openai
OPENAI_API_KEY=your_openai_key

# Azure OpenAI (if using)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8011
```

## Practice Modes

| Mode | Description |
|------|-------------|
| **Free Talk** | Natural conversation on any topic |
| **Corrective** | Get gentle grammar corrections |
| **Roleplay** | Practice scenarios (job interview, restaurant, etc.) |
| **Guided** | Structured practice with questions |

## Project Structure

```
lira/
├── backend/
│   ├── app/
│   │   ├── agents/         # Voice agent, conversation logic
│   │   ├── api/            # FastAPI routes
│   │   ├── core/           # Config, settings
│   │   ├── models/         # Pydantic models
│   │   └── services/       # STT, TTS, LLM services
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   └── lib/            # API client, utilities
│   └── package.json
└── README.md
```

## Development Roadmap

- [x] **P0** - Audio pipeline (LiveKit ↔ Deepgram STT ↔ TTS)
- [x] **P1** - LangGraph + LLM response logic
- [x] **P2** - Filler audio for natural latency masking
- [ ] **P3** - Analytics + persistent user profiles
- [ ] **P4** - Production optimization & deployment

## License

MIT
