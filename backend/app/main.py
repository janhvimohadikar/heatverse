"""HEATVERSE API entry point.  Run from the backend folder:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, analytics, auth, cities, health, map as map_api, predictions, profile, safety, weather
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import init_app_tables

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_app_tables()  # creates users/predictions/alerts tables if they do not exist (never touches weather data)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=("HEATVERSE - heat-wave monitoring and early-warning project API. Risk scores are an informational "
                 "project metric, not an official warning. Predictions are DEMO output unless a trained model is connected."),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,   # only the configured frontend origins
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


for r in (health.router, cities.router, weather.router, analytics.router, map_api.router, auth.router,
          profile.router, predictions.router, safety.router, admin.router):
    app.include_router(r)
