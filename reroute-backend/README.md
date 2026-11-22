# Reroute Backend

This is the backend for the Reroute travel planning application.

## Quick Start (with Frontend)

**See [RUNNING_THE_APP.md](RUNNING_THE_APP.md) for detailed instructions** on running both backend and frontend together.

### Quick CLI Commands

```bash
# Terminal 1: Backend
cd /e/reroute/reroute-backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd /e/reroute/frontend
npm run dev
```

The API is available at http://localhost:8000/api/v1

---

## Structure
- `app/api/`: REST API routers
- `app/agents/`: LangGraph implementation and LLM gateway
- `app/db/`: Database models and session management
- `app/services/`: Business logic layer
- `migrations/`: Alembic database migrations

## Setup
1. `pip install -r requirements.txt` (or use your preferred package manager)
2. Copy `.env.example` to `.env` and configure your database and API keys.
3. Run migrations: `alembic upgrade head`
4. Start the server: `uvicorn app.main:app --reload`

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
