from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from coverready_api.config.settings import Settings, get_settings
from coverready_api.db import build_engine, build_session_maker, init_db
from coverready_api.routes import api_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app_settings.ensure_dirs()
    engine = build_engine(app_settings)
    session_maker = build_session_maker(engine)
    init_db(engine)

    app = FastAPI(title=app_settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_maker = session_maker
    app.include_router(api_router)
    return app


app = create_app()
