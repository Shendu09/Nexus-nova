"""
Production FastAPI server — wraps all DL modules.
Replaces: AWS Lambda handler
Runs on: Any Linux server, Docker, Railway, Render, etc.
"""

from __future__ import annotations
import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.config import settings
from src.embedder import get_embedder
from src.analyzer import AnomalyDetector
from src.triage import LogTriager
from src.classifier import SeverityClassifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Global singletons (loaded once at startup)
_detector: AnomalyDetector | None = None
_triager: LogTriager | None = None
_classifier: SeverityClassifier | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models at startup."""
    global _detector, _triager, _classifier
    logger.info("Loading models...")
    _detector = AnomalyDetector()
    _triager = LogTriager()
    _classifier = SeverityClassifier()
    get_embedder()
    logger.info("All models ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Nexus Nova API",
    description="AI-powered log triage — open source edition",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    log_lines: list[str] = Field(..., min_length=1, max_length=10000)
    source: str = Field(default="unknown", max_length=100)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TriageResponse(BaseModel):
    request_id: str
    source: str
    severity: str
    root_cause: str
    affected_components: list[str]
    evidence: list[str]
    next_steps: list[str]
    confidence: float
    anomalous_line_count: int
    total_line_count: int
    anomaly_method: str
    model_used: str
    processing_time_ms: float


def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Simple API key auth."""
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/health")
async def health() -> dict:
    """Health check — no auth required."""
    return {
        "status": "ok",
        "models": {
            "embedder": "loaded",
            "detector": "loaded" if _detector else "not loaded",
            "triager": "loaded" if _triager else "not loaded",
            "classifier": "loaded" if _classifier else "not loaded",
        },
    }


@app.post("/triage", response_model=TriageResponse)
async def triage_logs(
    request: TriageRequest,
    _: str = Depends(verify_api_key),
) -> TriageResponse:
    """
    Full log triage pipeline:
    1. Embed log lines
    2. Detect anomalies (LSTM → Autoencoder → z-score)
    3. Classify severity (BERT → keyword rules)
    4. Generate RCA (Mistral → rule-based fallback)
    """
    start = time.perf_counter()

    # Validate input size
    total_size = sum(len(l) for l in request.log_lines)
    if total_size > settings.max_log_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Log payload too large")

    # Step 1: Anomaly detection
    anomaly_result = _detector.detect(request.log_lines)
    logger.info(
        f"[{request.request_id}] Anomalies: {len(anomaly_result.anomalous_indices)} "
        f"/ {len(request.log_lines)} lines | method={anomaly_result.method}"
    )

    # Step 2: Severity classification
    anomalous_text = "\n".join(
        request.log_lines[i] for i in anomaly_result.anomalous_indices[:30]
    )
    severity_pred = _classifier.predict(anomalous_text or request.log_lines[0])

    # Step 3: LLM root cause analysis
    report = await _triager.analyze(
        request.log_lines,
        anomaly_result.anomalous_indices,
    )

    # Use BERT severity if it's more confident than LLM
    final_severity = (
        severity_pred.label
        if severity_pred.confidence > 0.8
        else report.severity
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"[{request.request_id}] Done in {elapsed_ms:.0f}ms | severity={final_severity}")

    return TriageResponse(
        request_id=request.request_id,
        source=request.source,
        severity=final_severity,
        root_cause=report.root_cause,
        affected_components=report.affected_components,
        evidence=report.evidence,
        next_steps=report.next_steps,
        confidence=max(severity_pred.confidence, report.confidence),
        anomalous_line_count=len(anomaly_result.anomalous_indices),
        total_line_count=len(request.log_lines),
        anomaly_method=anomaly_result.method,
        model_used=report.model_used,
        processing_time_ms=elapsed_ms,
    )


@app.get("/models/status")
async def model_status(_: str = Depends(verify_api_key)) -> dict:
    """Check which ML models are trained and loaded."""
    from pathlib import Path
    models_dir = settings.models_dir
    return {
        "lstm": (models_dir / "lstm.pt").exists(),
        "autoencoder": (models_dir / "autoencoder.pt").exists(),
        "severity_classifier": (models_dir / "severity_classifier").exists(),
        "ollama_model": settings.ollama_model,
    }
