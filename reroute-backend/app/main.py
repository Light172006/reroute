import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routers import auth as auth_router
from app.api.routers import trips as trips_router
from app.api.routers import agent as agent_router
from app.api.routers import places as places_router
from app.api.routers import expense as expense_router
from app.api.dependencies import get_current_user
from app.api.schemas.auth import UserOut

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup if using SQLite or fresh db
    try:
        from app.db.session import engine, Base
        import app.db.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning("Database schema check warning: %s", exc)
    yield
    from app.db.session import engine
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# Environment-driven CORS configuration
cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
] if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

# ---------------------------------------------------------------------
# API v1 Router (matches frontend NEXT_PUBLIC_API_URL = /api/v1)
# ---------------------------------------------------------------------
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router.router, prefix="/auth")
api_v1_router.include_router(trips_router.router, prefix="/trips")
api_v1_router.include_router(trips_router.items_router)                     # /api/v1/items/{item_id}
api_v1_router.include_router(agent_router.router)                           # /api/v1/agent/...
api_v1_router.include_router(agent_router.trip_agent_router, prefix="/trips") # /api/v1/trips/{trip_id}/...
api_v1_router.include_router(agent_router.proposal_router)                 # /api/v1/proposals/{proposal_id}
api_v1_router.include_router(agent_router.demo_router, prefix="/demo")     # /api/v1/demo/...
api_v1_router.include_router(places_router.router)                          # /api/v1/places/search
api_v1_router.include_router(expense_router.router)                         # /api/v1/expenses/{expense_id}


@api_v1_router.get("/me", response_model=UserOut)
async def me_v1(current_user=Depends(get_current_user)):
    return current_user


@api_v1_router.get("/health")
async def health_v1():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


app.include_router(api_v1_router)

# ---------------------------------------------------------------------
# Root mount for direct calls and test backwards compatibility
# ---------------------------------------------------------------------
app.include_router(auth_router.router, prefix="/auth")
app.include_router(trips_router.router, prefix="/trips")
app.include_router(trips_router.items_router)                     # /items/{item_id}
app.include_router(agent_router.router)                           # /agent/...
app.include_router(agent_router.trip_agent_router, prefix="/trips") # /trips/{trip_id}/...
app.include_router(agent_router.proposal_router)                 # /proposals/{proposal_id}
app.include_router(agent_router.demo_router, prefix="/demo")     # /demo/...
app.include_router(places_router.router)                          # /places/search
app.include_router(expense_router.router)                         # /expenses/{expense_id}


@app.get("/me", response_model=UserOut)
async def me_root(current_user=Depends(get_current_user)):
    return current_user


@app.get("/health")
async def health_root():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/")
async def root():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION, "docs": "/docs"}
