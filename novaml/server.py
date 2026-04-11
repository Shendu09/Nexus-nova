"""FastAPI REST server for novaml."""

from __future__ import annotations
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import novaml
from novaml._config import settings

logger = logging.getLogger(__name__)


class TriageRequest(BaseModel):
    """REST API request model."""

    log_lines: list[str]
    source: Optional[str] = None
    request_id: Optional[str] = None


# Global model instances
_pipeline = None


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Verify API key from header."""
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize models on startup."""
    global _pipeline
    logger.info("Loading models on startup...")
    _pipeline = novaml._get_pipeline()
    yield
    logger.info("Shutting down...")


app = FastAPI(title="novaml", version="0.1.0", lifespan=lifespan)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    """Health check endpoint (no auth required)."""
    return {"status": "ok"}


@app.get("/health")
async def health():
    """Health check with model status."""
    return {
        "status": "ok",
        "models_loaded": _pipeline is not None,
        "version": "0.1.0",
    }


@app.post("/triage")
async def triage_endpoint(
    request: TriageRequest,
    _: str = Depends(verify_api_key),
):
    """Full triage endpoint."""
    if not request.log_lines:
        raise HTTPException(status_code=400, detail="log_lines cannot be empty")

    if len(request.log_lines) > settings.max_log_lines_per_request:
        raise HTTPException(
            status_code=413,
            detail=f"Too many log lines (max {settings.max_log_lines_per_request})",
        )

    try:
        start = time.perf_counter()
        result = _pipeline.triage(request.log_lines)
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "request_id": request.request_id,
            "severity": result.severity.value,
            "root_cause": result.root_cause,
            "affected_components": result.affected_components,
            "evidence": result.evidence,
            "next_steps": result.next_steps,
            "confidence": result.confidence,
            "anomalous_line_count": result.anomalous_line_count,
            "total_line_count": result.total_line_count,
            "processing_ms": elapsed,
            "model_used": result.model_used,
        }
    except Exception as e:
        logger.error(f"Triage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect")
async def detect_endpoint(
    request: TriageRequest,
    _: str = Depends(verify_api_key),
):
    """Anomaly detection endpoint."""
    try:
        result = _pipeline.detect(request.log_lines)
        return {
            "request_id": request.request_id,
            "scores": result.scores,
            "anomalous_indices": result.anomalous_indices,
            "threshold": result.threshold,
            "method": result.method,
            "total_lines": result.total_lines,
        }
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain")
async def explain_endpoint(
    request: TriageRequest,
    _: str = Depends(verify_api_key),
):
    """Explainability endpoint."""
    try:
        result = _pipeline.explain(request.log_lines)
        return {
            "request_id": request.request_id,
            "top_signals": result.top_signals,
            "token_scores": result.token_scores,
            "anomalous_patterns": result.anomalous_patterns,
            "explanation_text": result.explanation_text,
        }
    except Exception as e:
        logger.error(f"Explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/status")
async def models_status(_: str = Depends(verify_api_key)):
    """Check which models are trained."""
    from pathlib import Path

    model_dir = settings.models_dir_expanded
    return {
        "lstm_trained": (model_dir / "lstm_anomaly.pt").exists(),
        "autoencoder_trained": (model_dir / "autoencoder.pt").exists(),
        "classifier_trained": (model_dir / "classifiers" / "pytorch_model.bin").exists(),
        "models_dir": str(model_dir),
    }


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the uvicorn server."""
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=settings.api_workers,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    start_server()
