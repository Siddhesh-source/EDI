# Explainable Algorithmic Trading System

A rule-based trading platform that combines real-time market data analysis, sentiment analysis from news sources, technical indicators, and market regime detection to generate trading signals with complete explainability.

## Project Structure

```
.
├── src/
│   ├── sentiment/       # NewsAPI sentiment analyzer
│   ├── events/          # Event detector
│   ├── indicators/      # C++ Technical indicator engine
│   ├── regime/          # Market regime detector
│   ├── signal/          # Signal aggregator and CMS computation
│   ├── backtest/        # Backtesting module
│   ├── executor/        # Order executor (Kite Connect)
│   ├── api/             # FastAPI backend
│   ├── database/        # Database connection and repositories
│   └── shared/          # Shared data models and utilities
├── dashboard/           # React dashboard (frontend)
├── tests/               # Test suite
├── docker-compose.yml   # Docker configuration for Redis and PostgreSQL
├── init_db.sql          # Database initialization script
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template

```

## Setup

### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
```

### 3. Start Infrastructure Services

```bash
# Start Redis and PostgreSQL using Docker Compose
docker-compose up -d

# Check services are running
docker-compose ps
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m property
pytest -m integration
```

## Architecture

The system follows a microservices-inspired architecture with:

- **Redis Pub/Sub Pipeline**: Real-time data streaming between components
- **PostgreSQL Database**: Persistent storage for historical data and analysis
- **FastAPI Backend**: REST API and WebSocket server
- **C++ Technical Indicator Engine**: High-performance indicator computation
- **React Dashboard**: Real-time monitoring and visualization

## Key Features

- **Real-time Sentiment Analysis**: Processes financial news from NewsAPI
- **Event Detection**: Identifies significant market events
- **Technical Analysis**: Computes RSI, MACD, Bollinger Bands, and more
- **Market Regime Detection**: Classifies market conditions
- **Composite Market Score (CMS)**: Unified signal combining all analysis
- **Complete Explainability**: Every trading decision includes detailed reasoning
- **Backtesting**: Validate strategies against historical data
- **Live Trading**: Execute trades via Zerodha Kite Connect API

## Development

### Running the System

```bash
# Start the FastAPI backend
uvicorn src.api.main:app --reload

# Access API documentation
# http://localhost:8000/docs
```

### Running the Dashboard

```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Access dashboard
# http://localhost:3000
```

For detailed dashboard setup and features, see [dashboard/README.md](dashboard/README.md)

### Testing

The system uses a dual testing approach:

- **Unit Tests**: Verify specific examples and edge cases
- **Property-Based Tests**: Verify universal properties using Hypothesis

```bash
# Run property-based tests
pytest -m property

# Run with verbose output
pytest -v
```

## License

MIT
