"""Test fixtures and configuration."""

import pytest
import numpy as np


@pytest.fixture
def sample_logs():
    """20 sample log lines."""
    return [
        "INFO: Application started successfully",
        "INFO: Server listening on port 8080",
        "DEBUG: Processing request from 192.168.1.1",
        "DEBUG: Database connection pool initialized",
        "INFO: User login: admin@example.com",
        "INFO: Request processed in 234ms",
        "INFO: Cache hit rate: 87%",
        "WARNING: High memory usage detected",
        "WARNING: Database response time: 1500ms",
        "INFO: Batch job completed",
        "INFO: 1000 records processed",
        "ERROR: Connection to external API failed",
        "ERROR: Timeout waiting for response",
        "ERROR: Database transaction rolled back",
        "WARNING: Retry attempt 1/3",
        "INFO: Service health check passed",
        "INFO: Metrics exported successfully",
        "DEBUG: Configuration loaded from /etc/app.conf",
        "INFO: All background jobs completed",
        "INFO: Graceful shutdown initiated",
    ]


@pytest.fixture
def anomalous_logs():
    """Logs with anomalies."""
    return [
        "INFO: Normal operation",
        "INFO: Request processed",
        "ERROR: Out of memory! Process terminated",
        "ERROR: java.lang.OutOfMemoryError: heap space",
        "FATAL: Segmentation fault (core dumped)",
        "ERROR: Connection refused - unable to reach database",
        "ERROR: Unhandled exception in main loop",
        "CRITICAL: System panic - shutting down",
        "ERROR: File /data/critical.db not found",
    ]


@pytest.fixture
def mock_embeddings():
    """Mock numpy array of embeddings."""
    return np.random.randn(10, 384)
