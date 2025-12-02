# Design Document

## Overview

The Explainable Algorithmic Trading System is a distributed, real-time trading platform built on a microservices-inspired architecture. The system processes multiple data streams (market prices, news articles, technical indicators) through a Redis-based pub/sub pipeline, aggregates them into a Composite Market Score (CMS), and executes trades through the Zerodha Kite Connect API. Every component is designed for low latency, high throughput, and complete explainability.

The architecture emphasizes:
- **Performance**: C++ modules for compute-intensive operations, Redis for sub-10ms data delivery
- **Reliability**: Graceful degradation, error isolation, persistent storage
- **Explainability**: Every trading decision includes detailed reasoning with component breakdowns
- **Modularity**: Loosely coupled components communicating through well-defined interfaces

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          React Dashboard (Frontend)                      │
│                     WebSocket + REST API (Tailwind CSS)                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTP/WebSocket
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                         FastAPI Backend (Python)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐│
│  │   Signal     │  │  Backtest    │  │    Order     │  │   Config    ││
│  │ Aggregator   │  │  Orchestrator│  │  Executor    │  │  Manager    ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘│
└────────────┬───────────────────┬───────────────────┬────────────────────┘
             │                   │                   │
             │                   │                   │ Kite Connect API
             │                   │                   │
             │                   │              ┌────▼─────────────────┐
             │                   │              │   Zerodha Kite       │
             │                   │              │   Connect API        │
             │                   │              └──────────────────────┘
             │                   │
             │                   │
┌────────────▼───────────────────▼───────────────────▼────────────────────┐
│                          Redis Pub/Sub Pipeline                          │
│  Channels: prices | sentiment | events | signals | indicators | regime  │
└────────────┬───────────────────┬───────────────────┬────────────────────┘
             │                   │                   │
    ┌────────▼────────┐  ┌───────▼────────┐  ┌──────▼──────────┐
    │   NewsAPI       │  │   Technical     │  │    Market       │
    │   Sentiment     │  │   Indicator     │  │    Regime       │
    │   Analyzer      │  │   Engine (C++)  │  │    Detector     │
    │   (Python)      │  │                 │  │    (Python)     │
    └────────┬────────┘  └───────┬─────────┘  └──────┬──────────┘
             │                   │                    │
             │                   │                    │
             └───────────────────┴────────────────────┘
                                 │
                                 │
                    ┌────────────▼─────────────┐
                    │   PostgreSQL Database    │
                    │  - Historical prices     │
                    │  - News articles         │
                    │  - Sentiment scores      │
                    │  - Trading signals       │
                    │  - Executed orders       │
                    │  - Backtest results      │
                    └──────────────────────────┘
```

### Data Flow Overview

1. **Market Data Ingestion**: Price data flows from Kite Connect API → Redis `prices` channel → Technical Indicator Engine
2. **News Processing**: NewsAPI.org → Sentiment Analyzer → Redis `sentiment` channel + Event Detector → Redis `events` channel
3. **Technical Analysis**: Technical Indicator Engine (C++) computes indicators → Redis `indicators` channel
4. **Regime Detection**: Market Regime Detector analyzes price patterns → Redis `regime` channel
5. **Signal Generation**: FastAPI Signal Aggregator subscribes to all channels → Computes CMS → Publishes to Redis `signals` channel
6. **Order Execution**: Order Executor subscribes to `signals` channel → Validates → Executes via Kite Connect API
7. **Persistence**: All components write to PostgreSQL for historical analysis and auditing
8. **Dashboard Updates**: React Dashboard receives real-time updates via WebSocket from FastAPI Backend

## Components and Interfaces

### 1. NewsAPI Sentiment Analyzer (Python)

**Responsibilities:**
- Fetch financial news articles from NewsAPI.org
- Extract sentiment using rule-based NLP (keyword dictionaries, negation handling)
- Publish sentiment scores to Redis

**Interface:**
```python
class SentimentAnalyzer:
    def fetch_news(self, symbols: List[str], lookback_hours: int) -> List[Article]
    def analyze_sentiment(self, article: Article) -> SentimentScore
    def publish_to_redis(self, sentiment: SentimentScore) -> None
```

**Data Model:**
```python
@dataclass
class Article:
    id: str
    title: str
    content: str
    source: str
    published_at: datetime
    symbols: List[str]

@dataclass
class SentimentScore:
    article_id: str
    score: float  # -1.0 to +1.0
    confidence: float  # 0.0 to 1.0
    keywords_positive: List[str]
    keywords_negative: List[str]
    timestamp: datetime
```

**Redis Channel:** `sentiment`

### 2. Event Detector (Python)

**Responsibilities:**
- Scan news articles for predefined keywords
- Classify event types (earnings, merger, regulatory, etc.)
- Assign severity scores
- Publish high-priority events to Redis

**Interface:**
```python
class EventDetector:
    def detect_events(self, article: Article) -> List[Event]
    def classify_event(self, keywords: List[str]) -> EventType
    def compute_severity(self, event: Event) -> float
    def publish_to_redis(self, event: Event) -> None
```

**Data Model:**
```python
@dataclass
class Event:
    id: str
    article_id: str
    event_type: EventType  # EARNINGS, MERGER, ACQUISITION, BANKRUPTCY, REGULATORY
    severity: float  # 0.0 to 1.0
    keywords: List[str]
    timestamp: datetime

class EventType(Enum):
    EARNINGS = "earnings"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    BANKRUPTCY = "bankruptcy"
    REGULATORY = "regulatory"
    PRODUCT_LAUNCH = "product_launch"
    LEADERSHIP_CHANGE = "leadership_change"
```

**Redis Channel:** `events`

### 3. Technical Indicator Engine (C++)

**Responsibilities:**
- Compute technical indicators (RSI, MACD, Bollinger Bands, SMA, EMA, ATR)
- Generate technical signals based on threshold crossings
- Optimize for sub-50ms computation latency

**Interface (C++ with Python bindings via pybind11):**
```cpp
class TechnicalIndicatorEngine {
public:
    IndicatorResults compute_indicators(const PriceData& prices);
    TechnicalSignals generate_signals(const IndicatorResults& indicators);
    
private:
    double compute_rsi(const std::vector<double>& prices, int period);
    MACDResult compute_macd(const std::vector<double>& prices);
    BollingerBands compute_bollinger_bands(const std::vector<double>& prices, int period);
    double compute_atr(const std::vector<OHLC>& bars, int period);
};
```

**Data Model:**
```cpp
struct PriceData {
    std::string symbol;
    std::vector<OHLC> bars;
    int64_t timestamp;
};

struct OHLC {
    double open;
    double high;
    double low;
    double close;
    int64_t volume;
    int64_t timestamp;
};

struct IndicatorResults {
    double rsi;
    MACDResult macd;
    BollingerBands bollinger;
    double sma_20;
    double sma_50;
    double ema_12;
    double ema_26;
    double atr;
};

struct TechnicalSignals {
    SignalType rsi_signal;  // OVERBOUGHT, OVERSOLD, NEUTRAL
    SignalType macd_signal;  // BULLISH_CROSS, BEARISH_CROSS, NEUTRAL
    SignalType bb_signal;  // UPPER_BREACH, LOWER_BREACH, NEUTRAL
};
```

**Redis Channel:** `indicators`

### 4. Market Regime Detector (Python)

**Responsibilities:**
- Classify market regime using price action analysis
- Compute regime confidence scores
- Publish regime changes to Redis

**Interface:**
```python
class MarketRegimeDetector:
    def detect_regime(self, prices: List[OHLC], window: int = 100) -> MarketRegime
    def compute_confidence(self, regime: MarketRegime) -> float
    def publish_to_redis(self, regime: MarketRegime) -> None
```

**Data Model:**
```python
@dataclass
class MarketRegime:
    regime_type: RegimeType
    confidence: float  # 0.0 to 1.0
    volatility: float
    trend_strength: float
    timestamp: datetime

class RegimeType(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CALM = "calm"
```

**Redis Channel:** `regime`

### 5. Signal Aggregator (FastAPI Backend Component)

**Responsibilities:**
- Subscribe to all Redis channels
- Aggregate sentiment, technical, and regime data
- Compute Composite Market Score (CMS)
- Generate trading signals with explanations

**Interface:**
```python
class SignalAggregator:
    def aggregate_data(self) -> AggregatedData
    def compute_cms(self, data: AggregatedData) -> CompositeMarketScore
    def generate_signal(self, cms: CompositeMarketScore) -> TradingSignal
    def create_explanation(self, signal: TradingSignal) -> Explanation
```

**Data Model:**
```python
@dataclass
class AggregatedData:
    sentiment_score: float
    technical_signals: TechnicalSignals
    regime: MarketRegime
    events: List[Event]
    timestamp: datetime

@dataclass
class CompositeMarketScore:
    score: float  # -100 to +100
    sentiment_component: float
    technical_component: float
    regime_component: float
    weights: Dict[str, float]
    timestamp: datetime

@dataclass
class TradingSignal:
    signal_type: SignalType  # BUY, SELL, HOLD
    cms: CompositeMarketScore
    confidence: float
    explanation: Explanation
    timestamp: datetime

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class Explanation:
    summary: str
    sentiment_details: str
    technical_details: str
    regime_details: str
    event_details: str
    component_scores: Dict[str, float]
```

**CMS Computation Formula:**
```
CMS = (w_sentiment * sentiment_score * 100) + 
      (w_technical * technical_score * 100) + 
      (w_regime * regime_score * 100)

Where:
- w_sentiment = 0.3 (configurable)
- w_technical = 0.5 (configurable)
- w_regime = 0.2 (configurable)
- All scores normalized to [-1, 1] range before weighting
```

**Redis Channel:** `signals`

### 6. Backtesting Module (Python)

**Responsibilities:**
- Retrieve historical data from PostgreSQL
- Replay data chronologically
- Simulate signal generation and order execution
- Compute performance metrics

**Interface:**
```python
class BacktestingModule:
    def run_backtest(self, config: BacktestConfig) -> BacktestResult
    def load_historical_data(self, start: datetime, end: datetime) -> HistoricalData
    def simulate_trading(self, data: HistoricalData) -> List[Trade]
    def compute_metrics(self, trades: List[Trade]) -> PerformanceMetrics
```

**Data Model:**
```python
@dataclass
class BacktestConfig:
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    position_size: float
    cms_buy_threshold: float
    cms_sell_threshold: float

@dataclass
class BacktestResult:
    backtest_id: str
    config: BacktestConfig
    trades: List[Trade]
    metrics: PerformanceMetrics
    equity_curve: List[Tuple[datetime, float]]

@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    signal_type: SignalType

@dataclass
class PerformanceMetrics:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: timedelta
```

### 7. Order Executor (FastAPI Backend Component)

**Responsibilities:**
- Subscribe to trading signals
- Validate signals against risk management rules
- Execute orders via Kite Connect API
- Track order status and update database

**Interface:**
```python
class OrderExecutor:
    def validate_signal(self, signal: TradingSignal) -> bool
    def execute_order(self, signal: TradingSignal) -> Order
    def check_order_status(self, order_id: str) -> OrderStatus
    def handle_fill(self, order: Order) -> None
```

**Data Model:**
```python
@dataclass
class Order:
    order_id: str
    symbol: str
    order_type: OrderType  # MARKET, LIMIT
    side: Side  # BUY, SELL
    quantity: float
    price: Optional[float]
    status: OrderStatus
    signal_id: str
    timestamp: datetime

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class Side(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
```

### 8. Redis Pipeline

**Configuration:**
- **Channels**: `prices`, `sentiment`, `events`, `indicators`, `regime`, `signals`
- **Persistence**: RDB snapshots every 5 minutes + AOF for durability
- **Eviction Policy**: LRU when memory exceeds 80%
- **Max Memory**: 2GB (configurable)

**Pub/Sub Pattern:**
```python
# Publisher
redis_client.publish('sentiment', json.dumps(sentiment_score))

# Subscriber
pubsub = redis_client.pubsub()
pubsub.subscribe('sentiment', 'events', 'indicators', 'regime')
for message in pubsub.listen():
    handle_message(message)
```

### 9. PostgreSQL Database

**Schema:**

```sql
-- Prices table
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT,
    INDEX idx_symbol_timestamp (symbol, timestamp)
);

-- Articles table
CREATE TABLE articles (
    id VARCHAR(100) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    symbols TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sentiment scores table
CREATE TABLE sentiment_scores (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(100) REFERENCES articles(id),
    score DECIMAL(3, 2) NOT NULL,
    confidence DECIMAL(3, 2),
    keywords_positive TEXT[],
    keywords_negative TEXT[],
    timestamp TIMESTAMPTZ NOT NULL
);

-- Events table
CREATE TABLE events (
    id VARCHAR(100) PRIMARY KEY,
    article_id VARCHAR(100) REFERENCES articles(id),
    event_type VARCHAR(50) NOT NULL,
    severity DECIMAL(3, 2),
    keywords TEXT[],
    timestamp TIMESTAMPTZ NOT NULL
);

-- Trading signals table
CREATE TABLE trading_signals (
    id SERIAL PRIMARY KEY,
    signal_type VARCHAR(10) NOT NULL,
    cms_score DECIMAL(5, 2) NOT NULL,
    sentiment_component DECIMAL(5, 2),
    technical_component DECIMAL(5, 2),
    regime_component DECIMAL(5, 2),
    explanation JSONB,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20),
    side VARCHAR(10),
    quantity DECIMAL(10, 2),
    price DECIMAL(10, 2),
    status VARCHAR(20),
    signal_id INTEGER REFERENCES trading_signals(id),
    timestamp TIMESTAMPTZ NOT NULL
);

-- Backtest results table
CREATE TABLE backtest_results (
    id VARCHAR(100) PRIMARY KEY,
    config JSONB NOT NULL,
    metrics JSONB NOT NULL,
    trades JSONB NOT NULL,
    equity_curve JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 10. FastAPI Backend

**Endpoints:**

```python
# Health check
GET /health

# Get current CMS and signal
GET /api/v1/signal/current

# Get signal history
GET /api/v1/signal/history?start={start}&end={end}

# Run backtest
POST /api/v1/backtest
Body: BacktestConfig

# Get backtest results
GET /api/v1/backtest/{backtest_id}

# Get orders
GET /api/v1/orders?status={status}

# WebSocket for real-time updates
WS /ws/signals
```

**Middleware:**
- API Key Authentication
- CORS for React Dashboard
- Request logging
- Error handling

### 11. React Dashboard

**Components:**

1. **CMS Gauge**: Real-time gauge chart showing current CMS (-100 to +100)
2. **Signal Panel**: Current signal (BUY/SELL/HOLD) with color coding
3. **Explanation Panel**: Detailed breakdown of component scores
4. **Sentiment Panel**: Recent news articles with sentiment scores
5. **Technical Panel**: Current indicator values and signals
6. **Regime Panel**: Current market regime with confidence
7. **Order History**: Table of executed orders
8. **Backtest Panel**: Interface to run and view backtests

**Technology Stack:**
- React 18
- Tailwind CSS for styling
- Recharts for data visualization
- WebSocket for real-time updates
- Axios for REST API calls

## Data Models

All data models are defined in the Components and Interfaces section above. Key models include:

- `Article`, `SentimentScore` (News processing)
- `Event`, `EventType` (Event detection)
- `PriceData`, `OHLC`, `IndicatorResults`, `TechnicalSignals` (Technical analysis)
- `MarketRegime`, `RegimeType` (Regime detection)
- `AggregatedData`, `CompositeMarketScore`, `TradingSignal`, `Explanation` (Signal generation)
- `BacktestConfig`, `BacktestResult`, `Trade`, `PerformanceMetrics` (Backtesting)
- `Order`, `OrderType`, `Side`, `OrderStatus` (Order execution)


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Sentiment score bounds invariant
*For any* article processed by the NLP Sentiment Analyzer, the sentiment score must be within the range [-1.0, 1.0]
**Validates: Requirements 1.2**

### Property 2: Sentiment publishing completeness
*For any* article processed by the NLP Sentiment Analyzer, the sentiment score and article metadata must be published to the Redis `sentiment` channel
**Validates: Requirements 1.3**

### Property 3: Concurrent article processing
*For any* set of N articles submitted simultaneously, the total processing time should be less than N times the average single-article processing time, demonstrating concurrent processing
**Validates: Requirements 1.4**

### Property 4: Event severity bounds invariant
*For any* event detected by the Event Detector, the severity score must be within the range [0.0, 1.0]
**Validates: Requirements 2.2**

### Property 5: High-severity event alerting
*For any* event with severity greater than 0.7, a high-priority alert must be published to the Redis `events` channel
**Validates: Requirements 2.3**

### Property 6: Multiple event detection
*For any* article containing N distinct event keywords, the Event Detector must create N separate event records
**Validates: Requirements 2.4**

### Property 7: Technical indicator publishing
*For any* price data processed by the Technical Indicator Engine, the computed indicator values (RSI, MACD, Bollinger Bands, SMA, EMA, ATR) must be published to the Redis `indicators` channel
**Validates: Requirements 3.2**

### Property 8: Technical signal generation on threshold crossing
*For any* indicator values where RSI > 70 or RSI < 30 or MACD crosses zero, the Technical Indicator Engine must generate corresponding technical signals
**Validates: Requirements 3.3**

### Property 9: Historical indicator computation completeness
*For any* historical price dataset with N periods, the Technical Indicator Engine must compute indicators for all N periods
**Validates: Requirements 3.4**

### Property 10: Regime classification validity
*For any* price data analyzed by the Market Regime Detector, the classified regime must be one of: trending-up, trending-down, ranging, volatile, or calm
**Validates: Requirements 4.1**

### Property 11: Regime confidence bounds invariant
*For any* regime detection, the confidence score must be within the range [0.0, 1.0]
**Validates: Requirements 4.2**

### Property 12: Regime change publishing
*For any* price sequence that causes a regime change, the new regime must be published to the Redis `regime` channel
**Validates: Requirements 4.3**

### Property 13: Regime detection window size
*For any* regime detection operation, only the most recent 100 price bars should affect the classification result
**Validates: Requirements 4.4**

### Property 14: Low-confidence regime default
*For any* regime detection with confidence less than 0.6, the regime must be classified as "ranging"
**Validates: Requirements 4.5**

### Property 15: CMS bounds invariant
*For any* inputs to the CMS computation, the resulting Composite Market Score must be within the range [-100, 100]
**Validates: Requirements 5.2**

### Property 16: CMS signal generation rules
*For any* CMS value, the generated signal must be: BUY if CMS > 60, SELL if CMS < -60, or HOLD if -60 ≤ CMS ≤ 60
**Validates: Requirements 5.3, 5.4, 5.5**

### Property 17: Signal explanation completeness
*For any* trading signal generated, the explanation must include individual component scores (sentiment, technical, regime) and the weights applied to each component
**Validates: Requirements 5.6, 14.1, 14.2**

### Property 18: Backtest chronological replay
*For any* backtest execution, the historical data must be replayed in chronologically increasing order (no timestamp should precede a previous timestamp)
**Validates: Requirements 6.2**

### Property 19: Backtest metrics completeness
*For any* completed backtest, the results must include total return, Sharpe ratio, maximum drawdown, and win rate
**Validates: Requirements 6.3**

### Property 20: Backtest trade record completeness
*For any* trade generated during backtesting, the trade record must include entry price, exit price, holding period, and profit/loss
**Validates: Requirements 6.4**

### Property 21: Backtest result persistence
*For any* completed backtest, the results must be stored in the PostgreSQL Database with a unique backtest identifier
**Validates: Requirements 6.5**

### Property 22: Redis channel separation
*For any* data published to a specific Redis channel (prices, sentiment, events, signals, indicators, regime), the data must not appear in any other channel
**Validates: Requirements 7.2**

### Property 23: Redis subscription delivery
*For any* component subscribed to a Redis channel, all messages published to that channel after subscription must be delivered to the component
**Validates: Requirements 7.3**

### Property 24: Database record completeness
*For any* trading signal, executed order, processed article, or computed indicator, all required fields must be stored in the PostgreSQL Database
**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 25: API authentication enforcement
*For any* request received by the FastAPI Backend, authentication must be performed using API key validation
**Validates: Requirements 9.1**

### Property 26: Backtest request delegation
*For any* backtest request received by the FastAPI Backend, the request must be delegated to the Backtesting Module
**Validates: Requirements 9.4**

### Property 27: API error response format
*For any* error encountered by the FastAPI Backend, the response must include an appropriate HTTP status code and a detailed error message
**Validates: Requirements 9.5**

### Property 28: Dashboard CMS visualization
*For any* CMS value displayed on the React Dashboard, the gauge chart must use green color for positive values and red color for negative values
**Validates: Requirements 10.3**

### Property 29: Dashboard component panel separation
*For any* signal displayed on the React Dashboard, the sentiment score, technical indicator signals, and market regime must be shown in separate panels
**Validates: Requirements 10.4**

### Property 30: Order validation before execution
*For any* BUY or SELL signal generated, the Order Executor must validate the signal against risk management rules before submitting the order
**Validates: Requirements 11.1**

### Property 31: Order submission completeness
*For any* order placed by the Order Executor, the order must be submitted to Kite Connect API with symbol, quantity, and order type
**Validates: Requirements 11.2**

### Property 32: Order confirmation persistence
*For any* order confirmed by Kite Connect API, the order ID and status must be stored in the PostgreSQL Database
**Validates: Requirements 11.3**

### Property 33: Order status update on fill
*For any* order that is filled, the Order Executor must update the order status in the database
**Validates: Requirements 11.4**

### Property 34: C++ engine data format acceptance
*For any* price data sent from FastAPI Backend to the Technical Indicator Engine, the data must be accepted in the defined binary format
**Validates: Requirements 12.2**

### Property 35: C++ engine output format
*For any* computation completed by the Technical Indicator Engine, the results must be returned in a structured format parseable by Python
**Validates: Requirements 12.3**

### Property 36: Error logging completeness
*For any* error encountered by any component, the error log must include timestamp, component name, error type, and stack trace
**Validates: Requirements 13.1**

### Property 37: Technical indicator explanation detail
*For any* signal with technical triggers, the explanation must list the specific technical indicators that triggered the signal (e.g., "RSI crossed below 30")
**Validates: Requirements 14.3**

### Property 38: Event explanation completeness
*For any* detected news event included in a signal, the explanation must include event type, severity, and relevant keywords
**Validates: Requirements 14.4**

## Error Handling

The system implements comprehensive error handling with graceful degradation:

### 1. External Service Failures

**NewsAPI Service Unavailability:**
- System continues operating with cached sentiment data
- Sentiment marked as "stale" with timestamp of last update
- Periodic retry attempts with exponential backoff
- Alert sent to dashboard when service is down for > 5 minutes

**Kite Connect API Unavailability:**
- Automatic trading immediately disabled
- User notified via dashboard alert
- System continues generating signals for monitoring
- Manual trading still possible when API recovers

### 2. Infrastructure Failures

**Redis Pipeline Unavailability:**
- Components buffer data locally in memory (max 1000 messages)
- Automatic reconnection with exponential backoff (max 5 attempts)
- Buffered data replayed upon reconnection
- If buffer overflows, oldest messages dropped with warning log

**PostgreSQL Database Unavailability:**
- Write operations queued in memory (max 10,000 operations)
- Retry with exponential backoff (initial: 1s, max: 60s)
- Critical operations (order execution) logged to file as backup
- System continues operating in degraded mode

### 3. Component Failures

**Technical Indicator Engine Errors:**
- Invalid input data rejected with error code
- Fallback to previous indicator values if computation fails
- Error logged with input data for debugging
- Signal generation continues with available data

**Sentiment Analyzer Errors:**
- Failed article processing logged and skipped
- Sentiment component excluded from CMS if unavailable
- CMS reweighted to use only available components
- System continues with technical and regime analysis

### 4. Data Quality Issues

**Invalid Price Data:**
- Data validation before processing (non-negative prices, valid timestamps)
- Outlier detection using statistical methods (> 3 standard deviations)
- Invalid data rejected and logged
- Gap filling using last known good value

**Malformed News Articles:**
- Article validation (required fields present)
- Encoding error handling (UTF-8 fallback)
- Truncated content handled gracefully
- Failed articles logged and skipped

### 5. Performance Degradation

**High Latency Detection:**
- Performance monitoring for all critical paths
- Alerts when latency exceeds thresholds (sentiment: 5s, indicators: 50ms, CMS: 200ms)
- Automatic scaling recommendations logged
- Circuit breaker pattern for failing components

**Memory Pressure:**
- Redis LRU eviction when memory > 80%
- Component memory monitoring
- Garbage collection tuning for Python components
- Alert when system memory > 90%

## Testing Strategy

The system employs a dual testing approach combining unit tests and property-based tests to ensure comprehensive coverage and correctness.

### Unit Testing

Unit tests verify specific examples, integration points, and edge cases:

**Sentiment Analyzer:**
- Test sentiment extraction for known positive/negative articles
- Test keyword dictionary matching
- Test negation handling ("not good" → negative)
- Test empty article handling

**Event Detector:**
- Test keyword matching for each event type
- Test severity scoring for known events
- Test multiple event detection in single article

**Technical Indicator Engine:**
- Test RSI calculation with known price sequences
- Test MACD crossover detection
- Test Bollinger Band breach detection
- Test indicator computation with minimum data requirements

**Market Regime Detector:**
- Test regime classification for known trending/ranging markets
- Test confidence scoring
- Test regime transition detection

**Signal Aggregator:**
- Test CMS computation with known component scores
- Test signal generation at threshold boundaries
- Test explanation generation

**Order Executor:**
- Test risk management validation
- Test order submission to Kite Connect API (mocked)
- Test order status tracking

**Backtesting Module:**
- Test chronological data replay
- Test performance metric computation
- Test trade record generation

### Property-Based Testing

Property-based tests verify universal properties across all inputs using **Hypothesis** (Python) and **RapidCheck** (C++):

**Configuration:**
- Minimum 100 iterations per property test
- Shrinking enabled for minimal failing examples
- Seed-based reproducibility for debugging

**Property Test Requirements:**
- Each property test MUST be tagged with a comment: `# Feature: explainable-algo-trading, Property X: [property text]`
- Each correctness property MUST be implemented by a SINGLE property-based test
- Tests MUST use smart generators that constrain to valid input spaces

**Example Property Test Structure:**

```python
from hypothesis import given, strategies as st

# Feature: explainable-algo-trading, Property 1: Sentiment score bounds invariant
@given(article=st.builds(Article, ...))
def test_sentiment_score_bounds(article):
    sentiment = analyzer.analyze_sentiment(article)
    assert -1.0 <= sentiment.score <= 1.0
```

**Generator Strategies:**

*Price Data Generator:*
```python
@st.composite
def price_data(draw):
    n_bars = draw(st.integers(min_value=100, max_value=1000))
    base_price = draw(st.floats(min_value=10.0, max_value=1000.0))
    bars = []
    for _ in range(n_bars):
        open_price = base_price * draw(st.floats(min_value=0.95, max_value=1.05))
        high = open_price * draw(st.floats(min_value=1.0, max_value=1.02))
        low = open_price * draw(st.floats(min_value=0.98, max_value=1.0))
        close = draw(st.floats(min_value=low, max_value=high))
        bars.append(OHLC(open_price, high, low, close, ...))
    return PriceData(bars=bars)
```

*Article Generator:*
```python
@st.composite
def article(draw):
    sentiment_words = draw(st.lists(
        st.sampled_from(['bullish', 'bearish', 'positive', 'negative', ...]),
        min_size=1, max_size=10
    ))
    content = ' '.join(sentiment_words)
    return Article(title=draw(st.text()), content=content, ...)
```

**Property Test Coverage:**
- All 38 correctness properties will have corresponding property-based tests
- Edge cases (error handling, boundary conditions) covered by unit tests
- Integration tests verify component interactions

### Integration Testing

Integration tests verify end-to-end workflows:

- News article → Sentiment analysis → Redis → Signal generation
- Price data → Technical indicators → Redis → Signal generation
- Signal generation → Order execution → Database persistence
- Backtest request → Data retrieval → Simulation → Results storage
- WebSocket connection → Real-time updates → Dashboard display

### Performance Testing

Performance tests validate latency requirements:

- Sentiment analysis: < 5 seconds per article
- Event detection: < 100 milliseconds per article
- Technical indicators: < 50 milliseconds per computation
- Redis delivery: < 10 milliseconds
- Database writes: < 100 milliseconds
- API response: < 200 milliseconds for signal requests

### Testing Tools

- **pytest**: Python unit and integration testing
- **Hypothesis**: Python property-based testing
- **RapidCheck**: C++ property-based testing for Technical Indicator Engine
- **pytest-benchmark**: Performance testing
- **pytest-asyncio**: Async testing for FastAPI
- **pytest-redis**: Redis testing with fixtures
- **pytest-postgresql**: PostgreSQL testing with fixtures

## Deployment Architecture

### Development Environment

- Docker Compose orchestrating all services
- Hot reload for Python and React components
- Local Redis and PostgreSQL instances
- Mock Kite Connect API for testing

### Production Environment

- Kubernetes cluster for orchestration
- Redis Cluster for high availability
- PostgreSQL with replication (primary + 2 replicas)
- FastAPI deployed with Gunicorn + Uvicorn workers
- React Dashboard served via Nginx
- Prometheus + Grafana for monitoring
- ELK stack for centralized logging

### Monitoring and Observability

**Metrics:**
- Component latency (p50, p95, p99)
- Redis pub/sub throughput
- Database query performance
- Order execution success rate
- Signal generation frequency
- API request rate and errors

**Alerts:**
- External service unavailability
- Component latency exceeding thresholds
- Database connection failures
- Order execution failures
- Memory/CPU usage > 90%

**Logging:**
- Structured JSON logging
- Correlation IDs for request tracing
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized log aggregation

## Security Considerations

- API key authentication for all FastAPI endpoints
- HTTPS/TLS for all external communications
- Kite Connect API credentials stored in environment variables
- Database credentials managed via secrets management
- Rate limiting on API endpoints
- Input validation and sanitization
- SQL injection prevention via parameterized queries
- XSS prevention in React Dashboard

## Scalability Considerations

- Horizontal scaling of FastAPI workers
- Redis Cluster for distributed caching
- PostgreSQL read replicas for query scaling
- Asynchronous processing for non-blocking operations
- Message queuing for high-throughput scenarios
- CDN for React Dashboard static assets
- Connection pooling for database and Redis
