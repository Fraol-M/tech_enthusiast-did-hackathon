from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect

from .config import get_settings
from .database import Base, SessionLocal, engine
from .seed import seed_demo_data
from .services.esignet_verification import ESignetVerificationService
from .services.verify_client import InjiVerifyClient


settings = get_settings()
verify_client = InjiVerifyClient(settings)
esignet_service = ESignetVerificationService(settings)


def assert_supported_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "eligibility" in table_names:
        inspector.get_columns("eligibility")
    if "redemptions" in table_names:
        inspector.get_columns("redemptions")
    if "grievances" in table_names:
        inspector.get_columns("grievances")
    if "issuance_sessions" in table_names:
        inspector.get_columns("issuance_sessions")


@asynccontextmanager
async def lifespan(_app) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    assert_supported_schema()
    with SessionLocal() as db:
        seed_demo_data(db)
    yield
