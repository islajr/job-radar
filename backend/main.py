import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from backend.database import init_db
from backend.routers import auth, profile, dashboard, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.include_router(auth.router,      prefix="/api/auth")
app.include_router(profile.router,   prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router,     prefix="/api/admin")

# Ensure frontend/dist exists to avoid FastAPI StaticFiles startup crash
dist_dir = "frontend/dist"
if not os.path.exists(dist_dir):
    os.makedirs(dist_dir, exist_ok=True)
    with open(os.path.join(dist_dir, "index.html"), "w") as f:
        f.write("<!-- Placeholder for built React app -->")

app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
