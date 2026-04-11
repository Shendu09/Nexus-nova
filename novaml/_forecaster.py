"""Forecasting module with Prophet."""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from novaml._models import ForecastResult

logger = logging.getLogger(__name__)


class LogForecaster:
    """Time-series forecasting using Prophet."""

    def __init__(self) -> None:
        self._model = None
        self._models_cache: dict = {}

    def forecast(
        self, metric_df: Any, horizon_minutes: int = 60
    ) -> ForecastResult:
        """
        Forecast future metric anomalies.

        Args:
            metric_df: DataFrame with 'ds' (datetime) and 'y' (value) columns
            horizon_minutes: How far ahead to forecast

        Returns:
            ForecastResult with predictions and breach probability
        """
        try:
            from prophet import Prophet
            import pandas as pd

            logger.info(f"Forecasting {horizon_minutes} minutes ahead")

            # Convert to Prophet format if needed
            if "ds" not in metric_df.columns or "y" not in metric_df.columns:
                logger.warning("DataFrame missing 'ds' or 'y' columns")
                return ForecastResult(
                    predicted_values=[],
                    timestamps=[],
                    breach_probability=0.0,
                    trend="unknown",
                    model_used="failed",
                )

            # Suppress Prophet's verbose output
            import logging as py_logging
            py_logging.getLogger("prophet").setLevel(py_logging.WARNING)

            model = Prophet(interval_width=0.95)
            model.fit(metric_df)

            # Make future dataframe
            future = model.make_future_dataframe(periods=horizon_minutes, freq="min")
            forecast = model.predict(future)

            # Extract results
            forecast = forecast.tail(horizon_minutes)
            predicted_values = forecast["yhat"].tolist()
            timestamps = forecast["ds"].tolist()

            # Compute breach probability
            breach_probability = self._compute_breach_probability(forecast)

            # Estimate breach time
            estimated_breach_time = None
            for i, row in forecast.iterrows():
                if row["yhat_upper"] > metric_df["y"].max() * 1.5:
                    estimated_breach_time = row["ds"]
                    break

            # Detect trend
            recent_trend = forecast["trend"].iloc[-1] - forecast["trend"].iloc[0]
            if recent_trend > 0:
                trend = "rising"
            elif recent_trend < 0:
                trend = "falling"
            else:
                trend = "stable"

            return ForecastResult(
                predicted_values=predicted_values,
                timestamps=timestamps,
                breach_probability=min(1.0, breach_probability),
                estimated_breach_time=estimated_breach_time,
                trend=trend,
                model_used="prophet",
            )

        except ImportError:
            logger.warning("Prophet not installed. Install with: pip install 'novaml[forecast]'")
            return ForecastResult(
                predicted_values=[],
                timestamps=[],
                breach_probability=0.0,
                trend="unknown",
                model_used="unavailable",
            )
        except Exception as e:
            logger.error(f"Forecasting failed: {e}")
            return ForecastResult(
                predicted_values=[],
                timestamps=[],
                breach_probability=0.0,
                trend="unknown",
                model_used="failed",
            )

    def _compute_breach_probability(self, forecast: Any) -> float:
        """Compute probability of breach based on confidence intervals."""
        try:
            # Simple heuristic: if upper bound exceeds reasonable threshold
            breaches = (forecast["yhat_upper"] > forecast["yhat"] * 1.2).sum()
            total = len(forecast)
            return float(breaches) / float(max(total, 1))
        except Exception:
            return 0.0
