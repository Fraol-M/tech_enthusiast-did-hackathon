from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal, engine, get_db
from .domain.operations import get_current_cycle_record, get_current_eligibility_for_enrollment
from .domain.verification import determine_business_status
from .routers import routers
from .runtime import esignet_service, lifespan, settings, verify_client


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in routers:
    app.include_router(router)


__all__ = [
    "SessionLocal",
    "app",
    "determine_business_status",
    "engine",
    "esignet_service",
    "get_current_cycle_record",
    "get_current_eligibility_for_enrollment",
    "get_db",
    "settings",
    "verify_client",
]
