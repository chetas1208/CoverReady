from fastapi import APIRouter

from coverready_api.routes import broker_packet, claims, documents, events, evidence, health, scenarios, scorecards, translator, workspaces


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(workspaces.router, tags=["workspaces"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(claims.router, tags=["claims"])
api_router.include_router(scorecards.router, tags=["scorecards"])
api_router.include_router(translator.router, tags=["translator"])
api_router.include_router(scenarios.router, tags=["scenarios"])
api_router.include_router(broker_packet.router, tags=["broker-packet"])
