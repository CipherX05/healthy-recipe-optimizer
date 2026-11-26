"""Read-only JSON API over the local database. It never calls external sources.

Run with: python -m recipe_optimizer serve
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import config
from .db import DatabaseNotReady
from .service import NotFound, Service

log = logging.getLogger(__name__)


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    health: float = Field(ge=0, le=100)
    flavor: float = Field(ge=0, le=100)
    cuisine: float = Field(ge=0, le=100)
    role: float = Field(ge=0, le=100)


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: Literal["satFat", "calories", "protein", "fiber"]
    scope: Literal["ingredient", "recipe"] = "recipe"
    line_id: int | None = None
    weights: Weights | None = None
    selections: dict[int, str | None] = Field(default_factory=dict, max_length=60)
    ratios: dict[int, float] = Field(default_factory=dict, max_length=60)
    min_flavor: float = Field(default=0, ge=0, le=1)
    min_cuisine: float = Field(default=0, ge=0, le=1)
    keep_title_ingredients: bool = True
    guardrails: bool = True


def create_app(db_path: Path | str | None = None) -> FastAPI:
    service = Service(db_path)
    app = FastAPI(title="Recipe substitution API", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    def error(status: int, message: str) -> JSONResponse:
        return JSONResponse({"detail": message}, status_code=status)

    @app.exception_handler(DatabaseNotReady)
    def not_ready(_: Request, exc: DatabaseNotReady):
        return error(503, str(exc))

    @app.exception_handler(NotFound)
    def missing(_: Request, exc: NotFound):
        return error(404, str(exc))

    @app.exception_handler(sqlite3.Error)
    def broken(_: Request, exc: sqlite3.Error):
        log.exception("database error: %s", exc)
        return error(503, "The recipe database could not be read. Rebuild it and try again.")

    @app.get("/api/health")
    def health():
        return service.health()

    @app.get("/api/regions")
    def regions():
        return service.regions()

    @app.get("/api/recipes")
    def recipes(
        q: str = Query("", max_length=120),
        region: str = Query("", max_length=80),
        ingredient: str = Query("", max_length=80),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return service.search(query=q, region=region, ingredient=ingredient,
                              limit=limit, offset=offset)

    @app.get("/api/recipes/{recipe_id}")
    def recipe(recipe_id: int):
        return service.recipe(recipe_id)

    @app.post("/api/recipes/{recipe_id}/recommend")
    def recommend(recipe_id: int, request: RecommendRequest):
        try:
            return service.evaluate(
                recipe_id, request.goal, scope=request.scope, line_id=request.line_id,
                weights=request.weights.model_dump() if request.weights else None,
                selections=request.selections, ratios=request.ratios,
                min_flavor=request.min_flavor, min_cuisine=request.min_cuisine,
                keep_title_ingredients=request.keep_title_ingredients,
                guardrails=request.guardrails,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/ingredients/{ingredient_id}/network")
    def ingredient_network(ingredient_id: str, limit: int = Query(12, ge=1, le=40),
                           region: str = Query("", max_length=80)):
        return service.ingredient_network(ingredient_id, limit=limit, region=region)

    return app


app = create_app()
