"""
Jentic Personal Edition — main.py
FastAPI entry point. Skeleton that boots clean; routes added incrementally.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=os.getenv("LOG_LEVEL", "info").upper())
log = logging.getLogger("jpe")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Jentic Personal Edition starting up")
    # TODO: init DB, build BM25 index
    yield
    log.info("Jentic Personal Edition shutting down")


app = FastAPI(
    title="Jentic Personal Edition",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
