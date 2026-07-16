from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.mqtt_client import get_mqtt_client, start_mqtt, stop_mqtt
from app.scripts.init_db import init_db
from app.routers import (
    analytics,
    auth,
    classrooms,
    courseware,
    crops,
    dashboard,
    device_nodes,
    device_tokens,
    experiments,
    exports,
    groups,
    logs,
    mcp,
    notifications,
    pest_diagnoses,
    rules,
    sensors,
    student,
    submissions,
    tasks,
    teaching_resources,
    users,
    ws,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    if settings.AUTO_CREATE_DB:
        init_db()
    start_mqtt()
    from app.core.websocket_manager import ws_manager
    import asyncio
    ws_manager.set_loop(asyncio.get_running_loop())
    yield
    # 关闭时
    stop_mqtt()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()] if settings.CORS_ORIGINS else []
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins if _cors_origins != ["*"] else ["*"],
        allow_credentials=_cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    client = get_mqtt_client()
    mqtt_status = "connected" if client and client.is_connected() else "disconnected"
    return {"status": "ok", "mqtt": mqtt_status}


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(device_nodes.router, prefix=settings.API_V1_STR)
app.include_router(device_tokens.router, prefix=settings.API_V1_STR)
app.include_router(sensors.router, prefix=settings.API_V1_STR)
app.include_router(rules.router, prefix=settings.API_V1_STR)
app.include_router(crops.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(logs.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(classrooms.router, prefix=settings.API_V1_STR)
app.include_router(groups.router, prefix=settings.API_V1_STR)
app.include_router(submissions.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(courseware.router, prefix=settings.API_V1_STR)
app.include_router(teaching_resources.router, prefix=settings.API_V1_STR)
app.include_router(experiments.router, prefix=settings.API_V1_STR)
app.include_router(student.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(exports.router, prefix=settings.API_V1_STR)
app.include_router(pest_diagnoses.router, prefix=settings.API_V1_STR)
app.include_router(mcp.router, prefix=settings.API_V1_STR)
app.include_router(ws.router)

_avatar_dir = Path("data/avatars")
_avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(_avatar_dir)), name="avatars")

_courseware_dir = Path("data/courseware")
_courseware_dir.mkdir(parents=True, exist_ok=True)
app.mount("/courseware-files", StaticFiles(directory=str(_courseware_dir)), name="courseware-files")

_resources_dir = Path("data/resources")
_resources_dir.mkdir(parents=True, exist_ok=True)
app.mount("/resource-files", StaticFiles(directory=str(_resources_dir)), name="resource-files")

_submissions_dir = Path("data/submissions")
_submissions_dir.mkdir(parents=True, exist_ok=True)
app.mount("/submission-files", StaticFiles(directory=str(_submissions_dir)), name="submission-files")

_pest_images_dir = Path("data/pest-images")
_pest_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/pest-images", StaticFiles(directory=str(_pest_images_dir)), name="pest-images")
