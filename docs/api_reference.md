"""API reference documentation."""

# novaml API Reference

## Main Functions

### triage(logs, model="mistral", explain=True)
Full AI-powered log triage - detects anomalies, classifies severity, and provides RCA.

**Args:**
- logs: List of log strings or multiline string
- model: LLM model to use (default: mistral via Ollama)
- explain: Whether to include explainability (default: True)

**Returns:**
- TriageResult with severity, root_cause, next_steps, etc.

### detect(logs)
Detect anomalous log lines using deep learning.

**Args:**
- logs: List of log strings

**Returns:**
- AnomalyResult with scores and anomalous_indices

### explain(logs)
Explain WHY logs are anomalous using SHAP + signal extraction.

**Args:**
- logs: List of log strings

**Returns:**
- ExplainResult with top_signals and patterns

### forecast(metric_df, horizon_minutes=60)
Predict future metric anomalies with Prophet.

**Args:**
- metric_df: DataFrame with 'ds' and 'y' columns
- horizon_minutes: Forecast horizon

**Returns:**
- ForecastResult with predictions and breach probability

### train(logs, save_dir="~/.novaml/models")
Train unsupervised anomaly detector on your logs.

**Args:**
- logs: List of normal log lines
- save_dir: Where to save model weights

**Returns:**
- Dict with model_path and threshold

### serve(host="0.0.0.0", port=8000)
Start REST API server.
