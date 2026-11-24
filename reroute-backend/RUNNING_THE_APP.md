# Running Reroute: Backend + Frontend Together

This guide walks you through running both the FastAPI backend and the Next.js frontend together for local development.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option A: Mock Mode (No Real API Keys Required)](#option-a-mock-mode-no-real-api-keys-required)
3. [Option B: Full Mode with Real LLM APIs](#option-b-full-mode-with-real-llm-apis)
4. [Running Both Servers Together](#running-both-servers-together)
5. [Troubleshooting](#troubleshooting)
6. [Production Notes](#production-notes)

---

## Prerequisites

### System Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18.0+ | Frontend runtime |
| **npm** | 9.0+ | Frontend package manager |
| **PostgreSQL** | 15+ | Database server |
| **Docker** | 24+ (optional) | Containerized dev environment |

### Install PostgreSQL

**Windows (using pgAdmin):**
1. Download pgAdmin from [pgadmin.org](https://www.pgadmin.org/)
2. Run pgAdmin, right-click "PostgreSQL", select "Create → Server"
3. Set password: `postgres` (or your preferred password)

**macOS (using Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
```

---

## Option A: Mock Mode (No Real API Keys Required)

This is the fastest way to get started. The frontend runs fully functional with mock SSE streams and simulated data.

### Step 1: Set Up PostgreSQL Database

```bash
# Create the database and user
psql -U postgres -c "ALTER USER postgres PASSWORD 'postgres';"
psql -U postgres -c "CREATE DATABASE reroute;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE reroute TO postgres;"
```

### Step 2: Configure Environment Variables

```bash
# Navigate to backend directory
cd /e/reroute/reroute-backend

# Copy the environment template (create if it doesn't exist)
cp .env.example .env
```

Edit `.env` - the default values work for mock mode:

```env
# Database connection
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reroute"

# JWT Authentication (change in production!)
SECRET_KEY="super-secret-key-change-me-in-production"

# Mock mode is ENABLED by default (no API keys needed)
MOCK_TOOLS=true

# Optional: real API keys (set to None for mock mode)
GOOGLE_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
```

**Note:** If `.env.example` doesn't exist, create it with the content above.

### Step 3: Install Backend Dependencies

```bash
# Install the reroute_agents package first
cd /e/reroute/agents
pip install -e .

# Install the backend
cd /e/reroute/reroute-backend
pip install -e .
```

### Step 4: Run Database Migrations

```bash
# Run Alembic migrations to create database tables
alembic upgrade head
```

### Step 5: Start the Backend Server

```bash
# Run with auto-reload for development
uvicorn app.main:app --reload --port 8000
```

The backend is now running at http://localhost:8000

### Step 6: Configure and Start the Frontend

```bash
# Navigate to frontend directory
cd /e/reroute/frontend

# Copy environment template
cp .env.example .env.local
```

Edit `.env.local` - the defaults enable mock mode:

```env
NEXT_PUBLIC_USE_MOCKS=true
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Install dependencies and start:

```bash
# Install frontend dependencies (first time only)
npm install

# Start the development server
npm run dev
```

The frontend is now running at http://localhost:3000

---

## Option B: Full Mode with Real LLM APIs

To use real AI models instead of mocks, you need API keys.

### Configure Real LLM API Keys

Edit `/e/reroute/reroute-backend/.env`:

```env
# Set MOCK_TOOLS to false to use real APIs
MOCK_TOOLS=false

# Choose at least one API key:
GOOGLE_API_KEY=your_google_api_key_here
# OR
GROQ_API_KEY=your_groq_api_key_here
# OR
OPENROUTER_API_KEY=your_openrouter_api_key_here

# For PostgreSQL checkpoint persistence (optional but recommended)
# The default in-memory checkpointer works, but for persistent sessions:
# DATABASE_URL already configured for this
```

### Frontend Configuration for Real Backend

Edit `/e/reroute/frontend/.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Start Both Services

Same as mock mode, but the backend will make real LLM API calls:

```bash
# Terminal 1: Backend
cd /e/reroute/reroute-backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd /e/reroute/frontend
npm run dev
```

---

## Running Both Servers Together

Open **two terminal windows** or use a terminal multiplexer like `tmux`.

### Terminal 1: Backend

```bash
cd /e/reroute/reroute-backend

# Optional: Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies (first time)
pip install -e /e/reroute/agents
pip install -e .

# Run migrations (first time or after schema changes)
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

**Backend Endpoints:**
- API Docs: http://localhost:8000/docs
- Alternative API Docs: http://localhost:8000/redoc
- Base URL: http://localhost:8000/api/v1

### Terminal 2: Frontend

```bash
cd /e/reroute/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

**Frontend URL:** http://localhost:3000

---

## Project Structure Reference

```
/e/reroute/
├── agents/                          # Reroute agent package (AI/LLM logic)
│   ├── reroute_agents/
│   │   ├── gateway.py               # SSE streaming interface
│   │   ├── llm.py                   # LLM configuration
│   │   ├── graphs/                  # LangGraph definitions
│   │   ├── nodes/                   # Graph node implementations
│   │   ├── rules/                   # Deterministic validation rules
│   │   └── repositories/            # Protocol interfaces
│   └── pyproject.toml
│
├── reroute-backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── api/routers/             # REST API route handlers
│   │   │   ├── agent.py             # SSE streaming endpoint
│   │   │   ├── auth.py              # Authentication routes
│   │   │   ├── trips.py             # Trip CRUD operations
│   │   │   └── places.py            # Place search API
│   │   ├── services/                # Business logic
│   │   │   ├── agent_gateway.py     # Facade over LangGraph
│   │   │   ├── agent_repositories.py # SQLAlchemy adapters
│   │   │   ├── run_runner.py        # Background task runner
│   │   │   └── sse_broker.py        # Event streaming
│   │   ├── db/
│   │   │   ├── session.py           # Database session
│   │   │   └── models.py            # SQLAlchemy models
│   │   └── core/config.py           # Pydantic settings
│   ├── alembic/                     # Database migrations
│   ├── alembic.ini
│   └── pyproject.toml
│
└── frontend/                        # Next.js frontend
    ├── src/
    │   ├── lib/api.ts               # API client (respects mock mode)
    │   ├── components/              # React components
    │   ├── hooks/                   # Custom hooks
    │   └── mocks/                   # MSW mock handlers
    ├── package.json
    └── next.config.mjs
```

---

## Troubleshooting

### Port Already in Use

**Backend port 8000:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>
```

**Frontend port 3000:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>
```

### Database Connection Error

```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Ensure PostgreSQL is running:
   ```bash
   # macOS (Homebrew)
   brew services restart postgresql@15
   
   # Windows (pgAdmin)
   # Open pgAdmin and ensure PostgreSQL service is running
   
   # Check connection
   psql -h localhost -U postgres -d reroute
   ```

2. If password rejected, update `.env`:
   ```env
   DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reroute"
   ```

### Alembic Migration Error

```
sqlalchemy.exc.ProgrammingError: (psycopg2.ProgrammingError) relation "users" does not exist
```

**Solution:** Run migrations:
```bash
cd /e/reroute/reroute-backend
alembic upgrade head
```

### Frontend Can't Connect to Backend

1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check `.env.local` in frontend:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```

3. Ensure CORS is not blocked (FastAPI default setup allows localhost)

### "Run not found" or SSE Connection Issues

1. Check backend logs for errors
2. Verify the run was created successfully
3. SSE endpoint: `/agent/runs/{run_id}/stream`

---

## Production Notes

### Running with Docker

```bash
cd /e/reroute/reroute-backend
docker build -t reroute-backend .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:password@host.docker.internal:5432/reroute" \
  -e SECRET_KEY="your-production-secret" \
  reroute-backend
```

### Environment Variables for Production

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | JWT signing key (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))")` |
| `MOCK_TOOLS` | ❌ | Set to `false` for production |
| `GOOGLE_API_KEY` | ⚠️ | If `MOCK_TOOLS=false` |
| `GROQ_API_KEY` | ⚠️ | If `MOCK_TOOLS=false` |
| `OPENROUTER_API_KEY` | ⚠️ | If `MOCK_TOOLS=false` |

### Deployment Reference

See `/e/reroute/reroute-backend/DEPLOYMENT.md` for:
- AWS ECS/Fargate deployment
- GitHub Actions CI/CD
- Docker setup
- Secrets management with AWS Secrets Manager

---

## Quick Start Cheat Sheet

```bash
# Terminal 1: Backend
cd /e/reroute/reroute-backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd /e/reroute/frontend
npm run dev
```

Ready! Visit:
- **Backend**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000