"""
Unit tests for time-series forecasting module.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

from nexus.models.forecaster import (
    TimeSeriesForecast,
    ForecastingEngine,
    ForecastPoint,
    MetricForecast
)


class TestTimeSeriesForecast:
    """Tests for TimeSeriesForecast class."""
    
    @pytest.fixture
    def forecaster(self):
        """Create forecaster instance."""
        return TimeSeriesForecast("cpu_utilization")
    
    def test_init_default(self, forecaster):
        """Test default initialization."""
        assert forecaster.metric_name == "cpu_utilization"
        assert forecaster.threshold == 85.0
        assert forecaster.interval_minutes == 5
        assert forecaster.forecast_horizon_hours == 1
    
    def test_init_custom_threshold(self):
        """Test custom threshold."""
        forecaster = TimeSeriesForecast("cpu_utilization", threshold=90.0)
        assert forecaster.threshold == 90.0
    
    def test_init_invalid_metric(self):
        """Test initialization with invalid metric."""
        with pytest.raises(ValueError):
            TimeSeriesForecast("invalid_metric")
    
    def test_supported_metrics(self):
        """Test that all supported metrics can be initialized."""
        for metric in TimeSeriesForecast.SUPPORTED_METRICS:
            forecaster = TimeSeriesForecast(metric)
            assert forecaster.metric_name == metric
    
    def test_prepare_data(self, forecaster):
        """Test data preparation."""
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(10)]
        values = [50.0, 55.0, 52.0, 60.0, 58.0, 62.0, 65.0, 68.0, 70.0, 72.0]
        
        df = forecaster.prepare_data(timestamps, values)
        
        assert len(df) == 10
        assert "ds" in df.columns
        assert "y" in df.columns
        assert list(df["y"].values) == values
    
    def test_prepare_data_length_mismatch(self, forecaster):
        """Test error on timestamp/value length mismatch."""
        timestamps = [datetime.now()] * 10
        values = [50.0] * 5  # Mismatch
        
        with pytest.raises(ValueError):
            forecaster.prepare_data(timestamps, values)
    
    @pytest.mark.skipif(not _prophet_check(), reason="Prophet not installed")
    def test_fit_and_forecast(self, forecaster):
        """Test fitting and forecasting."""
        # Create synthetic time series
        base_time = datetime.now()
        timestamps = [base_time - timedelta(hours=i) for i in range(168)]  # 7 days
        
        # Create pattern with weekly seasonality
        values = []
        for i in range(168):
            base = 50.0
            hour = (base_time - timedelta(hours=i)).hour
            daily = 10 * np.sin(2 * np.pi * hour / 24)
            noise = np.random.normal(0, 2)
            values.append(base + daily + noise)
        
        # Fit model
        forecaster.fit(timestamps, values)
        assert forecaster.model is not None
        
        # Generate forecast
        forecast_points = forecaster.forecast()
        assert len(forecast_points) > 0
        
        # Check forecast point structure
        point = forecast_points[0]
        assert isinstance(point, ForecastPoint)
        assert point.metric == "cpu_utilization"
        assert 0 <= point.likelihood_breach <= 1
    
    def test_default_thresholds(self):
        """Test default threshold values."""
        expected = {
            "cpu_utilization": 85.0,
            "memory_usage": 85.0,
            "error_rate": 5.0,
            "latency_p99": 1000.0,
            "requests_per_second": 10000.0
        }
        
        assert TimeSeriesForecast.DEFAULT_THRESHOLDS == expected
    
    def test_calculate_breach_likelihood_certain_breach(self, forecaster):
        """Test breach likelihood when threshold definitely breached."""
        likelihood = forecaster._calculate_breach_likelihood(
            lower_bound=100.0,  # Minimum possible value exceeds threshold
            upper_bound=110.0,
            point_estimate=105.0
        )
        
        assert likelihood == 1.0
    
    def test_calculate_breach_likelihood_no_breach(self, forecaster):
        """Test breach likelihood when threshold safe."""
        likelihood = forecaster._calculate_breach_likelihood(
            lower_bound=20.0,
            upper_bound=30.0,
            point_estimate=25.0
        )
        
        assert likelihood == 0.0
    
    def test_calculate_breach_likelihood_partial(self, forecaster):
        """Test breach likelihood when threshold is within bounds."""
        # Forecaster has threshold of 85.0
        likelihood = forecaster._calculate_breach_likelihood(
            lower_bound=80.0,
            upper_bound=90.0,
            point_estimate=85.0
        )
        
        # Should be between 0 and 1
        assert 0 < likelihood < 1
    
    @pytest.mark.skipif(not _prophet_check(), reason="Prophet not installed")
    def test_save_and_load(self, forecaster):
        """Test model save and load."""
        # Fit a simple model
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(100)]
        values = [50.0 + np.random.normal(0, 5) for _ in range(100)]
        forecaster.fit(timestamps, values)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            forecaster.save(tmpdir)
            
            # Check files
            assert (Path(tmpdir) / "model.pkl").exists()
            assert (Path(tmpdir) / "metadata.json").exists()
            
            # Load
            loaded = TimeSeriesForecast.load(tmpdir)
            
            # Verify metadata
            assert loaded.metric_name == forecaster.metric_name
            assert loaded.threshold == forecaster.threshold


class TestForecastingEngine:
    """Tests for ForecastingEngine class."""
    
    def test_init(self):
        """Test engine initialization."""
        engine = ForecastingEngine()
        assert engine.forecasters == {}
    
    def test_custom_base_path(self):
        """Test custom base path."""
        engine = ForecastingEngine(base_path="./custom/path")
        assert engine.base_path == Path("./custom/path")
    
    @pytest.mark.skipif(not _prophet_check(), reason="Prophet not installed")
    def test_add_metric(self):
        """Test adding a metric."""
        engine = ForecastingEngine()
        
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(100)]
        values = [50.0 + np.random.normal(0, 5) for _ in range(100)]
        
        engine.add_metric("cpu_utilization", timestamps, values)
        
        assert "cpu_utilization" in engine.forecasters
        assert engine.forecasters["cpu_utilization"].model is not None


class TestForecastPoint:
    """Tests for ForecastPoint dataclass."""
    
    def test_forecast_point_creation(self):
        """Test creating forecast point."""
        point = ForecastPoint(
            timestamp="2024-01-01T12:00:00",
            metric="cpu_utilization",
            value=75.0,
            yhat_lower=70.0,
            yhat_upper=80.0,
            trend=2.0,
            likelihood_breach=0.3
        )
        
        assert point.timestamp == "2024-01-01T12:00:00"
        assert point.metric == "cpu_utilization"
        assert point.value == 75.0
        assert point.likelihood_breach == 0.3


class TestMetricForecast:
    """Tests for MetricForecast dataclass."""
    
    def test_metric_forecast_creation(self):
        """Test creating metric forecast."""
        points = [
            ForecastPoint(
                timestamp="2024-01-01T12:00:00",
                metric="cpu_utilization",
                value=75.0,
                yhat_lower=70.0,
                yhat_upper=80.0,
                trend=2.0,
                likelihood_breach=0.1
            )
        ]
        
        forecast = MetricForecast(
            metric="cpu_utilization",
            horizon_hours=1,
            threshold=85.0,
            forecast_points=points,
            breach_probability=0.1
        )
        
        assert forecast.metric == "cpu_utilization"
        assert len(forecast.forecast_points) == 1
        assert forecast.breach_probability == 0.1


def _prophet_check() -> bool:
    """Check if Prophet is available."""
    try:
        import prophet
        return True
    except ImportError:
        return False
