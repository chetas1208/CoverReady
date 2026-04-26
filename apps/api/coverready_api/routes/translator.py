from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from coverready_api.db import get_session
from coverready_api.schemas.api import TranslatorRequest, TranslatorResult
from coverready_api.services.translator import translate_clause


router = APIRouter(prefix="/translator")


@router.post("/explain", response_model=TranslatorResult)
def explain_clause(
    payload: TranslatorRequest, request: Request, session: Session = Depends(get_session)
) -> TranslatorResult:
    return translate_clause(session, request.app.state.settings, payload)

