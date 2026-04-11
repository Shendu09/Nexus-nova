CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(255),
    content TEXT NOT NULL,
    severity VARCHAR(20),
    anomaly_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_severity ON logs(severity);
CREATE INDEX idx_logs_source ON logs(source);

CREATE TABLE triage_reports (
    id SERIAL PRIMARY KEY,
    log_id INTEGER REFERENCES logs(id),
    severity VARCHAR(20) NOT NULL,
    root_cause TEXT,
    confidence FLOAT,
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reports_severity ON triage_reports(severity);
CREATE INDEX idx_reports_log_id ON triage_reports(log_id);
