# Nexus Nova API Reference

## Deep Learning Modules API

### Module 1: Autoencoder (Anomaly Detection)

#### Classes

**`AutoencoderModel`**
```python
class AutoencoderModel(nn.Module):
    """Unsupervised anomaly detection via reconstruction error."""
    
    def __init__(self, input_dim: int = 768, latent_dim: int = 64):
        """Initialize encoder-decoder architecture.
        
        Args:
            input_dim: Dimensionality of input embeddings (default 768)
            latent_dim: Dimensionality of latent space (default 64)
        """
        
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode input to latent representation."""
        
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent to reconstruction."""
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass returning reconstruction and latent."""
        
    def anomaly_score(self, x: torch.Tensor) -> float:
        """Compute normalized reconstruction error (0-1)."""
```

**`AnomalyDetector`**
```python
class AnomalyDetector:
    """Wrapper for anomaly detection on log embeddings."""
    
    def __init__(self, model: AutoencoderModel, threshold: float = 0.5):
        """
        Args:
            model: Trained autoencoder
            threshold: Anomaly score threshold (0-1)
        """
        
    def detect(self, embedding: np.ndarray) -> AnomalyDetectionResult:
        """
        Detect if log embedding is anomalous.
        
        Returns:
            is_anomalous: Boolean flag
            score: Reconstruction error (0-1)
            confidence: Confidence of detection
        """
```

### Module 2: BERT Classifier (Severity Classification)

#### Classes

**`SeverityClassifier`**
```python
class SeverityClassifier:
    """BERT-based severity classification (INFO/WARNING/HIGH/CRITICAL)."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize BERT-based classifier.
        
        Args:
            model_name: HuggingFace model ID
        """
        
    def predict(self, text: str) -> SeverityPrediction:
        """
        Classify single log/alert severity.
        
        Returns:
            severity: Integer (0=INFO, 1=WARNING, 2=HIGH, 3=CRITICAL)
            confidence: Float (0-1)
            logits: Dict of all class scores
        """
        
    def predict_batch(self, texts: List[str]) -> List[SeverityPrediction]:
        """Classify multiple texts in parallel."""
```

**`SeverityPrediction`** (Dataclass)
```python
@dataclass
class SeverityPrediction:
    severity: int  # 0-3 (INFO, WARNING, HIGH, CRITICAL)
    confidence: float  # 0-1
    logits: Dict[str, float]  # Per-class scores
```

#### Training API

**`SeverityClassifierTrainer`**
```python
class SeverityClassifierTrainer:
    """Fine-tune BERT on labeled severity data."""
    
    def __init__(self, config: SeverityClassifierConfig):
        """
        Args:
            config: Training configuration with lr, batch_size, epochs
        """
        
    def train(self, train_data: List[SeverityExample]) -> TrainingMetrics:
        """
        Fine-tune model on training data.
        
        Args:
            train_data: List of (text, label) pairs
            
        Returns:
            metrics: Training accuracy, val accuracy, final loss
        """
```

### Module 3: Time-Series Forecasting

#### Classes

**`TimeSeriesForecast`**
```python
class TimeSeriesForecast:
    """Facebook Prophet wrapper for metric forecasting."""
    
    def __init__(self, metric_name: str, threshold: float):
        """
        Args:
            metric_name: e.g., "CPU_Utilization", "Memory_Usage"
            threshold: Alert threshold for breach detection
        """
        
    def fit(self, historical_data: pd.DataFrame, periods: int = 30):
        """
        Fit Prophet model on historical metrics.
        
        Args:
            historical_data: DataFrame with 'ds' (timestamp) and 'y' (metric value)
            periods: Number of future periods to forecast
        """
        
    def predict(self, future_periods: int = 12) -> List[ForecastPoint]:
        """
        Generate future predictions.
        
        Returns:
            List of ForecastPoint with value, lower/upper bounds, trend
        """
```

**`ForecastPoint`** (Dataclass)
```python
@dataclass
class ForecastPoint:
    timestamp: datetime
    value: float  # Predicted value
    lower: float  # 95% lower bound
    upper: float  # 95% upper bound
    trend: str  # "up", "down", "stable"
    breach_likelihood: float  # P(value > threshold), 0-1
```

**`ForecastingEngine`**
```python
class ForecastingEngine:
    """Manage multi-metric forecasting."""
    
    def __init__(self, metric_configs: Dict[str, MetricConfig]):
        """
        Args:
            metric_configs: Dict of metric_name → (threshold, seasonality)
        """
        
    def forecast_all(self, future_hours: int = 24) -> Dict[str, MetricForecast]:
        """Forecast all configured metrics."""
```

### Module 4: LinUCB Bandit (Query Pre-fetching)

#### Classes

**`LinUCBAgent`**
```python
class LinUCBAgent:
    """Contextual bandit agent for learning optimal query selection."""
    
    def __init__(self, context_dim: int = 6, num_actions: int = 8, alpha: float = 0.5):
        """
        Args:
            context_dim: Feature dimension of incident context
            num_actions: Number of query types to choose from
            alpha: Exploration bonus coefficient
        """
        
    def select_action(self, context: np.ndarray) -> int:
        """
        Select top action given current context.
        
        Args:
            context: Feature vector of incident
            
        Returns:
            action_id: Selected query type (0-7)
        """
        
    def update(self, context: np.ndarray, action: int, reward: float):
        """
        Update agent parameters with feedback.
        
        Args:
            context: Incident context
            action: Selected action
            reward: Received reward (0-1)
        """
```

**`RLPrefetchStrategy`**
```python
class RLPrefetchStrategy:
    """High-level interface for prefetch planning."""
    
    def plan_prefetch(self, incident_type: str, severity: int) -> List[str]:
        """
        Get top-k recommended queries for incident investigation.
        
        Returns:
            List of query names ranked by expected utility
        """
        
    def record_feedback(self, action: str, was_helpful: bool, time_saved: float):
        """Record engineer feedback for learning."""
```

### Module 5: RLHF (Feedback & Preference Learning)

#### Classes

**`VoiceFeedback`** (Dataclass)
```python
@dataclass
class VoiceFeedback:
    suggestion_id: str
    quality_score: int  # 0-10
    relevance_score: float  # 0-1
    was_helpful: bool
    satisfaction: int  # 0-10
    timestamp: datetime
```

**`VoiceFeedbackCollector`**
```python
class VoiceFeedbackCollector:
    """Collect and store engineer voice feedback."""
    
    def record_feedback(self, feedback: VoiceFeedback) -> str:
        """
        Store feedback to DynamoDB.
        
        Returns:
            feedback_id: Unique identifier
        """
        
    def get_recent_feedback(self, hours: int = 24) -> List[VoiceFeedback]:
        """Retrieve recent feedback for training."""
```

**`RewardModel`**
```python
class RewardModel(nn.Module):
    """Predict engineer satisfaction from suggestion text."""
    
    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            input_ids: BERT token IDs
            
        Returns:
            reward: Scalar 0-1 satisfaction prediction
        """
```

**`DPOTrainer`**
```python
class DPOTrainer:
    """Direct Preference Optimization for alignment."""
    
    def train_step(self, batch: DPOBatch) -> float:
        """
        Single training step on preference pairs.
        
        Returns:
            loss: DPO loss value
        """
```

### Module 6: Embeddings (SimCSE Fine-tuning)

#### Classes

**`SimCSEEmbedder`**
```python
class SimCSEEmbedder:
    """Fine-tune sentence embeddings via contrastive learning."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """Initialize embedder with base model."""
        
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Returns:
            embeddings: (N, 768) numpy array
        """
        
    def encode_single(self, text: str) -> np.ndarray:
        """Encode single text to (768,) array."""
        
    def get_similarity(self, embeddings1: np.ndarray, 
                      embeddings2: np.ndarray) -> np.ndarray:
        """
        Compute pairwise similarity matrix.
        
        Returns:
            (N, M) cosine similarity matrix
        """
```

**`SimCSETrainer`**
```python
class SimCSETrainer:
    """Fine-tune embeddings with contrastive loss."""
    
    def train(self, train_texts: List[str], num_epochs: int = 3) -> TrainingStats:
        """
        Fine-tune model on log texts.
        
        Returns:
            stats: Training loss history
        """
```

**`LogEmbeddingStore`**
```python
class LogEmbeddingStore:
    """Store and retrieve embeddings with similarity search."""
    
    def add(self, log_id: str, embedding: np.ndarray):
        """Add log embedding to store."""
        
    def get_most_similar(self, query_embedding: np.ndarray, 
                        top_k: int = 10) -> List[str]:
        """
        Find most similar logs to query.
        
        Returns:
            List of log IDs ranked by similarity
        """
        
    def build_faiss_index(self):
        """Build FAISS index for fast retrieval."""
```

## Lambda Integration

### Handler Signature

```python
def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler for Nexus incidents.
    
    Event:
        incident_logs: List[str]
        service_name: str
        timestamp: int
        
    Returns:
        suggestions: List[Dict] with query recommendations
        severity: int (0-3)
        forecast_alerts: List[Dict]
        anomaly_score: float
    """
```

## Environment Variables

```
MODELS_BUCKET=nexus-ml-models  # S3 bucket for models
SNS_TOPIC_ARN=arn:aws:...      # SNS notifications
DYNAMODB_TABLE=nexus-ml-config # Config storage
REGION=us-east-1
LOG_LEVEL=INFO
```

## Error Handling

All modules raise consistent exceptions:
- `ModelNotFoundError`: Model files missing
- `InferenceError`: Inference failed
- `ConfigError`: Invalid configuration
- `AWSError`: AWS service unavailable

## Metrics & Monitoring

### CloudWatch Metrics
- `ModuleLatency` - Inference time per module (ms)
- `ModelAccuracy` - Classification accuracy (0-1)
- `ForecastError` - MAPE for Prophet forecasts
- `RewardModel - Correlation with actual feedback

### Logging
All modules log to `/var/log/nexus/` with DEBUG, INFO, WARNING levels.
