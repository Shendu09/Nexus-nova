"""
Time-Series Forecasting Module using Facebook's Prophet

This module provides proactive metric forecasting to predict when infrastructure
capacity will be exceeded before anomalies occur. Supports multiple metrics:
- CPU utilization
- Memory usage
- Error rate
- Latency

Uses Facebook's Prophet library for robust forecasting with:
- Automatic trend detection
- Seasonality modeling
- Holiday effects
- Confidence intervals (breach probability)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

try:
    from prophet import Prophet
    _prophet_available = True
except ImportError:
    _prophet_available = False

logger = logging.getLogger(__name__)


@dataclass
class ForecastPoint:
    """Single forecast data point."""
    timestamp: str
    metric: str
    value: float
    yhat_lower: float
    yhat_upper: float
    trend: float
    likelihood_breach: float  # Probability of exceeding threshold


@dataclass
class MetricForecast:
    """Complete forecast for a metric."""
    metric: str
    horizon_hours: int
    threshold: float
    forecast_points: List[ForecastPoint]
    breach_probability: float  # Probability of any breach in horizon
    estimated_breach_time: Optional[str] = None


class TimeSeriesForecast:
    """
    Time-series forecasting engine using Prophet.
    
    Predicts future metric values and calculates probability of
    breaching operational thresholds.
    """
    
    SUPPORTED_METRICS = [
        "cpu_utilization",
        "memory_usage",
        "error_rate",
        "latency_p99",
        "requests_per_second"
    ]
    
    # Default thresholds (can be overridden per environment)
    DEFAULT_THRESHOLDS = {
        "cpu_utilization": 85.0,      # percentage
        "memory_usage": 85.0,           # percentage
        "error_rate": 5.0,              # percentage
        "latency_p99": 1000.0,          # milliseconds
        "requests_per_second": 10000.0  # RPS
    }
    
    def __init__(
        self,
        metric_name: str,
        threshold: Optional[float] = None,
        interval_minutes: int = 5,
        forecast_horizon_hours: int = 1
    ):
        """
        Initialize forecaster for a specific metric.
        
        Args:
            metric_name: Name of metric to forecast
            threshold: Breach threshold (uses default if None)
            interval_minutes: Data collection interval (e.g., 5-minute metrics)
            forecast_horizon_hours: Lookahead window in hours
        """
        if metric_name not in self.SUPPORTED_METRICS:
            raise ValueError(f"Unsupported metric: {metric_name}")
        
        self.metric_name = metric_name
        self.threshold = threshold or self.DEFAULT_THRESHOLDS[metric_name]
        self.interval_minutes = interval_minutes
        self.forecast_horizon_hours = forecast_horizon_hours
        self.model: Optional[Prophet] = None
    
    def prepare_data(
        self,
        timestamps: List[datetime],
        values: List[float]
    ) -> pd.DataFrame:
        """
        Prepare data for Prophet.
        
        Args:
            timestamps: List of datetime objects
            values: List of metric values
            
        Returns:
            DataFrame with 'ds' (datetime) and 'y' (values) columns
        """
        if len(timestamps) != len(values):
            raise ValueError("Timestamp and value lists must be same length")
        
        return pd.DataFrame({
            "ds": timestamps,
            "y": values
        })
    
    def fit(
        self,
        timestamps: List[datetime],
        values: List[float],
        yearly_seasonality: bool = False,
        weekly_seasonality: bool = True
    ):
        """
        Fit Prophet model to historical data.
        
        Args:
            timestamps: Historical timestamps
            values: Historical metric values
            yearly_seasonality: Enable yearly seasonality
            weekly_seasonality: Enable weekly seasonality
        """
        if not _prophet_available:
            raise ImportError("Prophet not installed. Install with: pip install cmdstanpy prophet")
        
        # Prepare data
        df = self.prepare_data(timestamps, values)
        
        # Create and fit model
        self.model = Prophet(
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=True,
            interval_width=0.95,
            changepoint_prior_scale=0.05
        )
        
        self.model.fit(df)
        logger.info(f"Fitted Prophet model for {self.metric_name}")
    
    def forecast(
        self,
        horizon_hours: Optional[int] = None
    ) -> List[ForecastPoint]:
        """
        Generate forecast for future period.
        
        Args:
            horizon_hours: Forecast horizon (uses default if None)
            
        Returns:
            List of ForecastPoint objects
        """
        if self.model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        horizon = horizon_hours or self.forecast_horizon_hours
        periods = int((horizon * 60) / self.interval_minutes)
        
        # Generate forecast
        future_df = self.model.make_future_dataframe(periods=periods, freq=f"{self.interval_minutes}T")
        forecast_df = self.model.predict(future_df)
        
        # Filter to future only
        now = datetime.now()
        forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
        forecast_df = forecast_df[forecast_df["ds"] > now]
        
        # Convert to ForecastPoint objects
        points = []
        for _, row in forecast_df.iterrows():
            likelihood = self._calculate_breach_likelihood(
                row["yhat_lower"],
                row["yhat_upper"],
                row["yhat"]
            )
            
            point = ForecastPoint(
                timestamp=row["ds"].isoformat(),
                metric=self.metric_name,
                value=float(row["yhat"]),
                yhat_lower=float(row["yhat_lower"]),
                yhat_upper=float(row["yhat_upper"]),
                trend=float(row["trend"]),
                likelihood_breach=likelihood
            )
            points.append(point)
        
        return points
    
    def _calculate_breach_likelihood(
        self,
        lower_bound: float,
        upper_bound: float,
        point_estimate: float
    ) -> float:
        """
        Calculate probability that actual value will breach threshold.
        
        Uses prediction intervals from Prophet to estimate probability.
        
        Args:
            lower_bound: 95% confidence interval lower bound
            upper_bound: 95% confidence interval upper bound
            point_estimate: Point forecast (mean)
            
        Returns:
            Probability (0-1) of breaching threshold
        """
        if upper_bound < self.threshold:
            return 0.0
        elif lower_bound > self.threshold:
            return 1.0
        else:
            # Threshold is within confidence interval
            # Use normal distribution assumption
            std_dev = (upper_bound - lower_bound) / 3.92  # 95% CI ≈ ±1.96*std
            
            # Z-score for threshold
            z_score = (self.threshold - point_estimate) / std_dev if std_dev > 0 else 0
            
            # Convert to probability (CDF of standard normal)
            from scipy.stats import norm
            return float(norm.sf(z_score))  # Survival function (1 - CDF)
    
    def save(self, save_path: str):
        """Save fitted model to disk."""
        if self.model is None:
            raise RuntimeError("No model fitted yet")
        
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        self.model.save(str(save_path / "model.pkl"))
        
        # Save metadata
        metadata = {
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "interval_minutes": self.interval_minutes,
            "forecast_horizon_hours": self.forecast_horizon_hours,
            "fit_time": datetime.now().isoformat()
        }
        
        with open(save_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved forecast model to {save_path}")
    
    @classmethod
    def load(cls, save_path: str) -> "TimeSeriesForecast":
        """Load fitted model from disk."""
        if not _prophet_available:
            raise ImportError("Prophet not installed")
        
        save_path = Path(save_path)
        
        # Load metadata
        with open(save_path / "metadata.json") as f:
            metadata = json.load(f)
        
        # Create instance
        instance = cls(
            metric_name=metadata["metric_name"],
            threshold=metadata["threshold"],
            interval_minutes=metadata["interval_minutes"],
            forecast_horizon_hours=metadata["forecast_horizon_hours"]
        )
        
        # Load model
        instance.model = Prophet.load(str(save_path / "model.pkl"))
        
        logger.info(f"Loaded forecast model from {save_path}")
        return instance


class ForecastingEngine:
    """
    Multi-metric forecasting engine.
    
    Manages forecasting for all supported metrics and provides
    unified breach probability calculations.
    """
    
    def __init__(self, base_path: str = "./models/forecasts"):
        """Initialize forecasting engine."""
        self.base_path = Path(base_path)
        self.forecasters: Dict[str, TimeSeriesForecast] = {}
    
    def add_metric(
        self,
        metric_name: str,
        timestamps: List[datetime],
        values: List[float],
        threshold: Optional[float] = None
    ):
        """Add and fit forecaster for a metric."""
        forecaster = TimeSeriesForecast(metric_name, threshold=threshold)
        forecaster.fit(timestamps, values)
        self.forecasters[metric_name] = forecaster
    
    def forecast_all(self) -> Dict[str, MetricForecast]:
        """Generate forecasts for all metrics."""
        results = {}
        
        for metric_name, forecaster in self.forecasters.items():
            forecast_points = forecaster.forecast()
            
            # Calculate aggregate breach probability
            breach_probs = [p.likelihood_breach for p in forecast_points]
            aggregate_breach_prob = 1.0 - np.prod([1 - p for p in breach_probs])
            
            # Find estimated breach time
            breach_time = None
            for point in forecast_points:
                if point.likelihood_breach > 0.5:
                    breach_time = point.timestamp
                    break
            
            metric_forecast = MetricForecast(
                metric=metric_name,
                horizon_hours=forecaster.forecast_horizon_hours,
                threshold=forecaster.threshold,
                forecast_points=forecast_points,
                breach_probability=aggregate_breach_prob,
                estimated_breach_time=breach_time
            )
            
            results[metric_name] = metric_forecast
        
        return results
    
    def save_all(self):
        """Save all forecasters."""
        for metric_name, forecaster in self.forecasters.items():
            save_path = self.base_path / metric_name
            forecaster.save(str(save_path))
