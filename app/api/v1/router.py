"""Agrega todos os routers da v1 sob um único APIRouter."""

from fastapi import APIRouter

from . import auth, match, meta, parse_resume, salary_benchmark

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(parse_resume.router)
api_router.include_router(salary_benchmark.router)
api_router.include_router(match.router)
