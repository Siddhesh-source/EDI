# Setup Guide

This guide will help you set up the Explainable Algorithmic Trading System.

## Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- Git

## Quick Start

### Option 1: Automated Setup (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Option 2: Manual Setup

#### 1. Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Required: NEWSAPI_KEY, KITE_API_KEY, KITE_API_SECRET
```

#### 4. Start Infrastructure Services

```bash
# Start Redis and PostgreSQL
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs if needed
docker-compose logs -f
```

#### 5. Verify Installation

```bash
# Run tests to verify everything is working
pytest tests/test_project_structure.py -v
```

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
│       ├── models.py           # All data models
│       ├── config.py           # Configuration management
│       └── logging_config.py   # Logging setup
├── tests/               # Test suite
├── scripts/             # Setup scripts
├── docker-compose.yml   # Docker configuration
├── init_db.sql          # Database schema
├── requirements.txt     # Python dependencies
└── .env.example         # Environment template
```

## Configuration

### Environment Variables

Edit `.env` file with your configuration:

```bash
# Database (defaults work with Docker Compose)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=trading_password

# Redis (defaults work with Docker Compose)
REDIS_HOST=localhost
REDIS_PORT=6379

# NewsAPI (required - get from https://newsapi.org/)
NEWSAPI_KEY=your_key_here

# Kite Connect (required for live trading)
KITE_API_KEY=your_key_here
KITE_API_SECRET=your_secret_here
KITE_ACCESS_TOKEN=your_token_here

# API Configuration
API_KEY=your_secure_api_key
API_PORT=8000

# CMS Weights (adjust as needed)
CMS_WEIGHT_SENTIMENT=0.3
CMS_WEIGHT_TECHNICAL=0.5
CMS_WEIGHT_REGIME=0.2

# Signal Thresholds
CMS_BUY_THRESHOLD=60
CMS_SELL_THRESHOLD=-60

# Trading
ENABLE_AUTO_TRADING=false
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m property      # Property-based tests only
pytest -m integration   # Integration tests only

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src
```

## Docker Services

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Access Services

- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432
  - Database: trading_db
  - User: trading_user
  - Password: trading_password

### Connect to PostgreSQL
```bash
docker exec -it trading_postgres psql -U trading_user -d trading_db
```

### Connect to Redis
```bash
docker exec -it trading_redis redis-cli
```

## Next Steps

1. **Configure API Keys**: Edit `.env` with your NewsAPI and Kite Connect credentials
2. **Implement Components**: Follow the tasks in `.kiro/specs/explainable-algo-trading/tasks.md`
3. **Run Tests**: Ensure all tests pass as you implement features
4. **Start Development**: Begin with task 2 (database implementation)

## Troubleshooting

### Docker Services Not Starting

```bash
# Check Docker is running
docker --version
docker-compose --version

# Check for port conflicts
netstat -an | findstr "6379"  # Redis
netstat -an | findstr "5432"  # PostgreSQL

# View detailed logs
docker-compose logs redis
docker-compose logs postgres
```

### Import Errors

```bash
# Ensure virtual environment is activated
# Windows:
.\venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose ps

# Check database logs
docker-compose logs postgres

# Test connection
docker exec -it trading_postgres psql -U trading_user -d trading_db -c "SELECT 1;"
```

## Development Workflow

1. Activate virtual environment
2. Ensure Docker services are running
3. Implement feature according to tasks
4. Write tests (unit and property-based)
5. Run tests to verify
6. Commit changes

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Redis Documentation](https://redis.io/documentation)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [NewsAPI Documentation](https://newsapi.org/docs)
- [Kite Connect Documentation](https://kite.trade/docs/connect/v3/)
