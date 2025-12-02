"""Test project structure and imports."""

import pytest
from pathlib import Path


def test_project_root_exists():
    """Test that project root directory exists."""
    root = Path(__file__).parent.parent
    assert root.exists()


def test_src_directory_exists():
    """Test that src directory exists."""
    root = Path(__file__).parent.parent
    src_dir = root / "src"
    assert src_dir.exists()
    assert src_dir.is_dir()


def test_all_module_directories_exist():
    """Test that all module directories exist."""
    root = Path(__file__).parent.parent
    src_dir = root / "src"
    
    expected_modules = [
        "sentiment",
        "events",
        "indicators",
        "regime",
        "signal",
        "backtest",
        "executor",
        "api",
        "database",
        "shared",
    ]
    
    for module in expected_modules:
        module_dir = src_dir / module
        assert module_dir.exists(), f"Module directory {module} does not exist"
        assert module_dir.is_dir(), f"{module} is not a directory"
        
        # Check for __init__.py
        init_file = module_dir / "__init__.py"
        assert init_file.exists(), f"__init__.py missing in {module}"


def test_shared_models_import():
    """Test that shared models can be imported."""
    from src.shared.models import (
        Article,
        SentimentScore,
        Event,
        EventType,
        OHLC,
        MarketRegime,
        RegimeType,
        TradingSignal,
        TradingSignalType,
        TechnicalSignalType,
    )
    
    # Verify enums have expected values
    assert EventType.EARNINGS.value == "earnings"
    assert RegimeType.TRENDING_UP.value == "trending_up"
    assert TradingSignalType.BUY.value == "buy"
    assert TechnicalSignalType.OVERSOLD.value == "oversold"


def test_config_import():
    """Test that configuration can be imported."""
    from src.shared.config import Settings, settings
    
    assert isinstance(settings, Settings)
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "redis_url")


def test_logging_config_import():
    """Test that logging configuration can be imported."""
    from src.shared.logging_config import setup_logging, get_logger
    
    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "test"


def test_requirements_file_exists():
    """Test that requirements.txt exists."""
    root = Path(__file__).parent.parent
    requirements = root / "requirements.txt"
    assert requirements.exists()
    
    # Check that it contains key dependencies
    content = requirements.read_text()
    assert "fastapi" in content.lower()
    assert "redis" in content.lower()
    assert "psycopg2" in content.lower()
    assert "hypothesis" in content.lower()
    assert "pytest" in content.lower()


def test_docker_compose_exists():
    """Test that docker-compose.yml exists."""
    root = Path(__file__).parent.parent
    docker_compose = root / "docker-compose.yml"
    assert docker_compose.exists()
    
    content = docker_compose.read_text()
    assert "redis" in content.lower()
    assert "postgres" in content.lower()


def test_database_init_script_exists():
    """Test that database initialization script exists."""
    root = Path(__file__).parent.parent
    init_script = root / "init_db.sql"
    assert init_script.exists()
    
    content = init_script.read_text()
    assert "CREATE TABLE" in content
    assert "prices" in content
    assert "articles" in content
    assert "trading_signals" in content


@pytest.mark.unit
def test_data_model_instantiation():
    """Test that data models can be instantiated."""
    from datetime import datetime
    from src.shared.models import (
        Article,
        SentimentScore,
        Event,
        EventType,
        OHLC,
    )
    
    # Test Article
    article = Article(
        id="test-1",
        title="Test Article",
        content="Test content",
        source="Test Source",
        published_at=datetime.now(),
        symbols=["AAPL"],
    )
    assert article.id == "test-1"
    assert article.title == "Test Article"
    
    # Test SentimentScore
    sentiment = SentimentScore(
        article_id="test-1",
        score=0.5,
        confidence=0.8,
        keywords_positive=["growth", "profit"],
        keywords_negative=[],
        timestamp=datetime.now(),
    )
    assert sentiment.score == 0.5
    assert sentiment.confidence == 0.8
    
    # Test Event
    event = Event(
        id="event-1",
        article_id="test-1",
        event_type=EventType.EARNINGS,
        severity=0.8,
        keywords=["earnings", "report"],
        timestamp=datetime.now(),
    )
    assert event.event_type == EventType.EARNINGS
    assert event.severity == 0.8
    
    # Test OHLC
    ohlc = OHLC(
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000000,
        timestamp=datetime.now(),
    )
    assert ohlc.open == 100.0
    assert ohlc.close == 103.0
