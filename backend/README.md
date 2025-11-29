# LIRA Backend

Real-time voice-to-voice English speaking agent backend.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/sessions` - Create new session
- `GET /api/sessions/{id}` - Get session details
- `PATCH /api/sessions/{id}/mode` - Update session mode
- `DELETE /api/sessions/{id}` - End session
