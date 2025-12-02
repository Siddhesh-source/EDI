# Requirements Document

## Introduction

This document specifies the requirements for an Explainable Algorithmic Trading System (EATS) that combines NLP-based sentiment analysis, keyword-based event detection, rule-based technical indicators, market regime detection, and composite market scoring to generate explainable trading signals. The system is designed for research and production use, emphasizing transparency, performance, and extensibility without requiring machine learning model training.

## Glossary

- **EATS**: Explainable Algorithmic Trading System - the complete trading system
- **NLP Engine**: Natural Language Processing Engine - component that analyzes text for sentiment and events
- **Sentiment Index (SI)**: A numerical score (-1 to +1) representing market sentiment derived from text analysis
- **Event Shock Factor (ESF)**: A numerical score representing the impact magnitude of detected market events
- **Technical Indicator Engine**: Component that calculates mathematical indicators from price data
- **EMA**: Exponential Moving Average - a trend-following indicator
- **RSI**: Relative Strength Index - a momentum oscillator (0-100)
- **MACD**: Moving Average Convergence Divergence - a trend-following momentum indicator
- **Bollinger Bands**: Volatility bands placed above and below a moving average
- **ATR**: Average True Range - a volatility indicator
- **Market Regime**: Classification of current market state (Bull, Bear, Sideways, Panic)
- **CMS**: Composite Market Score - a fused score combining sentiment, volatility, trend, and events
- **Trading Engine**: Component that generates buy/sell/hold signals based on rules
- **Backtesting Engine**: Component that simulates historical trading performance
- **Redis Streaming Pipeline**: Real-time data distribution system using Redis Pub/Sub
- **PostgreSQL Storage**: Relational database for persistent data storage
- **C++ Acceleration Module**: High-performance compiled module for intensive calculations
- **FastAPI Backend**: Python-based REST API server
- **React Dashboard**: Web-based user interface for visualization and control
- **Stop-Loss**: Automatic exit price to limit losses
- **Trailing Stop**: Dynamic stop-loss that moves with favorable price movement
- **Position Sizing**: Calculation of trade quantity based on risk parameters
- **PnL**: Profit and Loss
- **CAGR**: Compound Annual Growth Rate
- **Sharpe Ratio**: Risk-adjusted return metric
- **Drawdown**: Peak-to-trough decline in portfolio value
- **Zerodha Kite Connect**: API service for live trading on Indian stock exchanges
- **KiteConnect**: Python SDK for Zerodha Kite Connect API
- **KiteTicker**: WebSocket client for real-time market data from Zerodha
- **Access Token**: Authentication token for Zerodha API access
- **Order**: Instruction to buy or sell a security
- **Position**: Currently held securities in a trading account
- **Holdings**: Long-term investments in a trading account
- **Margin**: Available funds for trading
- **NSE**: National Stock Exchange of India
- **BSE**: Bombay Stock Exchange
- **MIS**: Margin Intraday Square-off product type
- **CNC**: Cash and Carry product type for delivery trades

## Requirements

### Requirement 1: NLP-Based Sentiment Analysis

**User Story:** As a quantitative researcher, I want to analyze text data for market sentiment using lexicon-based methods, so that I can incorporate sentiment signals into trading decisions without training ML models.

#### Acceptance Criteria

1. WHEN the NLP Engine receives text input, THE EATS SHALL compute a Sentiment Index using a lexicon-based method (VADER or custom dictionary) with a score range of -1.0 to +1.0
2. WHEN the NLP Engine processes text, THE EATS SHALL normalize the text by removing special characters, converting to lowercase, and tokenizing into words
3. WHEN computing Sentiment Index, THE EATS SHALL aggregate individual word sentiment scores using weighted averaging based on word position and intensity modifiers
4. WHEN the Sentiment Index is calculated, THE EATS SHALL store the result with timestamp and source identifier in the PostgreSQL database
5. WHEN sentiment analysis completes, THE EATS SHALL publish the Sentiment Index to the Redis sentiment stream channel within 100 milliseconds

### Requirement 2: Keyword-Based Event Detection

**User Story:** As a trading system operator, I want to detect significant market events through keyword matching, so that I can react to news-driven market shocks.

#### Acceptance Criteria

1. WHEN the NLP Engine receives text input, THE EATS SHALL scan for predefined event keywords including "fraud", "acquisition", "merger", "bankruptcy", "revenue up", "revenue down", "lawsuit", "FDA approval", and "earnings beat"
2. WHEN an event keyword is detected, THE EATS SHALL calculate an Event Shock Factor with magnitude based on keyword severity and context window
3. WHEN multiple event keywords appear in the same text, THE EATS SHALL compute the combined Event Shock Factor as the sum of individual factors capped at magnitude 5.0
4. WHEN an event is detected, THE EATS SHALL store the event type, timestamp, source, and Event Shock Factor in the PostgreSQL events table
5. WHEN Event Shock Factor exceeds magnitude 2.0, THE EATS SHALL publish an alert to the Redis event stream channel immediately

### Requirement 3: Technical Indicator Calculation

**User Story:** As a technical analyst, I want the system to calculate standard technical indicators from price data, so that I can incorporate technical analysis into trading rules.

#### Acceptance Criteria

1. WHEN price data is available, THE EATS SHALL calculate EMA with configurable periods (default 20 and 50) using the formula: EMA(t) = Price(t) * k + EMA(t-1) * (1-k) where k = 2/(period+1)
2. WHEN price data spans at least 14 periods, THE EATS SHALL calculate RSI using the formula: RSI = 100 - (100 / (1 + RS)) where RS = average gain / average loss
3. WHEN price data is available, THE EATS SHALL calculate MACD as the difference between 12-period and 26-period EMAs, and calculate the signal line as a 9-period EMA of MACD
4. WHEN price data spans at least 20 periods, THE EATS SHALL calculate Bollinger Bands with middle band as 20-period SMA, upper band as middle + (2 * standard deviation), and lower band as middle - (2 * standard deviation)
5. WHEN price data spans at least 14 periods, THE EATS SHALL calculate ATR as the 14-period moving average of True Range, where True Range is the maximum of (High-Low, |High-PreviousClose|, |Low-PreviousClose|)
6. WHEN technical indicators are calculated, THE EATS SHALL store all indicator values with timestamp and symbol in the PostgreSQL database

### Requirement 4: Market Regime Detection

**User Story:** As a portfolio manager, I want the system to classify the current market regime, so that I can adapt trading strategies to market conditions.

#### Acceptance Criteria

1. WHEN volatility (measured by ATR/Price ratio) exceeds 0.05 AND Sentiment Index is below -0.5, THE EATS SHALL classify the market regime as "Panic"
2. WHEN EMA20 is greater than EMA50 AND RSI is between 40 and 70 AND volatility is below 0.03, THE EATS SHALL classify the market regime as "Bull"
3. WHEN EMA20 is less than EMA50 AND RSI is between 30 and 60 AND volatility is below 0.03, THE EATS SHALL classify the market regime as "Bear"
4. WHEN the absolute difference between EMA20 and EMA50 is less than 0.5% of price AND volatility is below 0.02, THE EATS SHALL classify the market regime as "Sideways"
5. WHEN market regime changes, THE EATS SHALL store the new regime with timestamp in the PostgreSQL regimes table and publish to the Redis regime stream channel

### Requirement 5: Composite Market Score Calculation

**User Story:** As a quantitative strategist, I want a unified market score that combines multiple signals, so that I can make holistic trading decisions based on a single interpretable metric.

#### Acceptance Criteria

1. WHEN all component scores are available, THE EATS SHALL calculate CMS using the formula: CMS = 0.4 * SentimentIndex - 0.3 * VolatilityIndex + 0.2 * TrendStrength + 0.1 * EventShockFactor
2. WHEN calculating VolatilityIndex, THE EATS SHALL normalize ATR by dividing by current price and scaling to range -1.0 to +1.0
3. WHEN calculating TrendStrength, THE EATS SHALL compute as (EMA20 - EMA50) / EMA50 and clip to range -1.0 to +1.0
4. WHEN calculating CMS, THE EATS SHALL normalize EventShockFactor to range -1.0 to +1.0 by dividing by maximum expected shock magnitude of 5.0
5. WHEN CMS is calculated, THE EATS SHALL store the value and all component scores with timestamp in the PostgreSQL cms_values table
6. WHEN CMS is calculated, THE EATS SHALL publish the CMS value to the Redis cms stream channel within 50 milliseconds

### Requirement 6: Rule-Based Trading Signal Generation

**User Story:** As a systematic trader, I want the system to generate buy/sell/hold signals based on explicit rules, so that I can execute trades with full transparency and explainability.

#### Acceptance Criteria

1. WHEN EMA20 is greater than EMA50 AND SentimentIndex is greater than 0.2 AND no negative event keywords are detected in the last 24 hours AND CMS is greater than 0.3, THE EATS SHALL generate a BUY signal
2. WHEN EMA20 is less than EMA50 AND SentimentIndex is less than -0.3 AND EventShockFactor is less than -1.0 AND CMS is less than -0.3, THE EATS SHALL generate a SELL signal
3. WHEN neither BUY nor SELL conditions are met, THE EATS SHALL generate a HOLD signal
4. WHEN a trading signal is generated, THE EATS SHALL include the signal type, timestamp, triggering conditions, and all component values in the signal record
5. WHEN a trading signal is generated, THE EATS SHALL store the signal in the PostgreSQL signals table and publish to the Redis signals stream channel

### Requirement 7: Risk Management with Stop-Loss

**User Story:** As a risk manager, I want automated stop-loss mechanisms to limit downside risk, so that I can protect capital during adverse market movements.

#### Acceptance Criteria

1. WHEN a BUY signal is executed, THE EATS SHALL calculate an ATR-based stop-loss price as entry_price - (2.0 * ATR)
2. WHEN a position is open and price moves favorably by at least 1.5 * ATR, THE EATS SHALL activate a trailing stop-loss that follows price at a distance of 1.5 * ATR
3. WHEN current price reaches or falls below the stop-loss price, THE EATS SHALL generate an immediate SELL signal with reason "stop-loss triggered"
4. WHEN a trailing stop is active and price moves favorably, THE EATS SHALL update the trailing stop-loss price to maintain the 1.5 * ATR distance
5. WHEN a stop-loss is triggered, THE EATS SHALL record the stop-loss event with entry price, exit price, and loss amount in the PostgreSQL trades table

### Requirement 8: Position Sizing Based on Risk

**User Story:** As a portfolio manager, I want position sizes calculated based on fixed risk per trade, so that I can maintain consistent risk exposure across all trades.

#### Acceptance Criteria

1. WHEN a BUY signal is generated, THE EATS SHALL calculate position size using the formula: position_size = (account_equity * risk_per_trade) / (entry_price - stop_loss_price)
2. WHEN calculating position size, THE EATS SHALL use a default risk_per_trade value of 0.02 (2% of account equity) unless configured otherwise
3. WHEN calculated position size exceeds maximum position limit, THE EATS SHALL cap the position size at the configured maximum limit
4. WHEN calculated position size is less than minimum tradeable quantity, THE EATS SHALL set position size to zero and mark the signal as non-tradeable
5. WHEN position size is calculated, THE EATS SHALL include the position size, risk amount, and calculation parameters in the signal record

### Requirement 9: Backtesting Engine with Performance Metrics

**User Story:** As a quantitative researcher, I want to simulate historical trading performance, so that I can evaluate strategy effectiveness before live deployment.

#### Acceptance Criteria

1. WHEN the Backtesting Engine receives historical price data in CSV format, THE EATS SHALL parse the data and validate that required columns (date, open, high, low, close, volume) are present
2. WHEN backtesting executes, THE EATS SHALL simulate trades by applying trading rules to each historical data point in chronological order
3. WHEN backtesting completes, THE EATS SHALL calculate and report PnL curve, win rate, CAGR, Sharpe ratio, and maximum drawdown
4. WHEN backtesting completes, THE EATS SHALL generate a trade log containing entry date, entry price, exit date, exit price, PnL, and exit reason for each simulated trade
5. WHEN backtesting completes, THE EATS SHALL output a price chart with buy/sell markers overlaid at trade entry and exit points
6. WHEN calculating Sharpe ratio, THE EATS SHALL use the formula: (mean_return - risk_free_rate) / std_deviation_of_returns, with annualization factor of sqrt(252) for daily returns
7. WHEN calculating maximum drawdown, THE EATS SHALL compute the largest peak-to-trough decline in cumulative portfolio value during the backtest period

### Requirement 10: PostgreSQL Data Storage Schema

**User Story:** As a data engineer, I want a well-structured relational database schema, so that I can efficiently store and query all system data.

#### Acceptance Criteria

1. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a historical_prices table with columns: id, symbol, timestamp, open, high, low, close, volume, and indexes on (symbol, timestamp)
2. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a sentiment_scores table with columns: id, timestamp, source, text_snippet, sentiment_index, and index on timestamp
3. WHEN the EATS initializes, THE PostgreSQL database SHALL contain an events table with columns: id, timestamp, source, event_type, keywords_matched, event_shock_factor, and index on timestamp
4. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a signals table with columns: id, timestamp, symbol, signal_type, cms_value, sentiment_index, trend_strength, volatility_index, event_shock_factor, and indexes on (symbol, timestamp)
5. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a trades table with columns: id, symbol, entry_timestamp, entry_price, exit_timestamp, exit_price, position_size, pnl, exit_reason, and indexes on (symbol, entry_timestamp)
6. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a cms_values table with columns: id, timestamp, symbol, cms_score, sentiment_component, volatility_component, trend_component, event_component, and index on (symbol, timestamp)
7. WHEN the EATS initializes, THE PostgreSQL database SHALL contain a regimes table with columns: id, timestamp, symbol, regime_type, volatility_level, trend_direction, and index on (symbol, timestamp)

### Requirement 11: Redis Streaming Pipeline

**User Story:** As a system architect, I want real-time data distribution using Redis, so that I can decouple components and enable low-latency data flow.

#### Acceptance Criteria

1. WHEN the EATS starts, THE Redis Streaming Pipeline SHALL create channels named "price:live", "sentiment:live", "cms:live", "signals:live", "events:live", and "regimes:live"
2. WHEN new price data arrives, THE EATS SHALL publish the data to the "price:live" channel in JSON format with fields: symbol, timestamp, price, volume
3. WHEN Sentiment Index is calculated, THE EATS SHALL publish to the "sentiment:live" channel in JSON format with fields: timestamp, symbol, sentiment_index, source
4. WHEN CMS is calculated, THE EATS SHALL publish to the "cms:live" channel in JSON format with fields: timestamp, symbol, cms_score, components
5. WHEN a trading signal is generated, THE EATS SHALL publish to the "signals:live" channel in JSON format with fields: timestamp, symbol, signal_type, cms_value, conditions
6. WHEN Redis publish operations fail, THE EATS SHALL retry up to 3 times with exponential backoff before logging an error

### Requirement 12: High-Performance C++ Acceleration Module

**User Story:** As a performance engineer, I want computationally intensive calculations performed in compiled C++ code, so that I can achieve low-latency processing for real-time trading.

#### Acceptance Criteria

1. WHEN the C++ Acceleration Module is invoked, THE module SHALL compute EMA for an array of prices with time complexity O(n) where n is the number of data points
2. WHEN the C++ Acceleration Module is invoked, THE module SHALL compute RSI for an array of prices with time complexity O(n)
3. WHEN the C++ Acceleration Module is invoked, THE module SHALL compute ATR for arrays of high, low, and close prices with time complexity O(n)
4. WHEN the C++ Acceleration Module is invoked, THE module SHALL compute rolling volatility (standard deviation) with time complexity O(n)
5. WHEN the C++ Acceleration Module is called from Python, THE EATS SHALL use pybind11 bindings to expose C++ functions with zero-copy array passing for NumPy arrays
6. WHEN the C++ Acceleration Module is built, THE build system SHALL produce a shared library (.so on Linux, .dll on Windows, .dylib on macOS) that Python can import
7. WHEN C++ calculations complete, THE module SHALL return results as NumPy-compatible arrays without data copying

### Requirement 13: FastAPI Backend REST Endpoints

**User Story:** As a frontend developer, I want a RESTful API to access system data and trigger operations, so that I can build interactive user interfaces.

#### Acceptance Criteria

1. WHEN a GET request is made to /price/live/{symbol}, THE FastAPI Backend SHALL return the most recent price data from Redis or PostgreSQL with response time under 100 milliseconds
2. WHEN a GET request is made to /sentiment/live/{symbol}, THE FastAPI Backend SHALL return the most recent Sentiment Index with timestamp and source
3. WHEN a GET request is made to /cms/live/{symbol}, THE FastAPI Backend SHALL return the most recent CMS value with all component scores
4. WHEN a GET request is made to /signals?symbol={symbol}&start={start}&end={end}, THE FastAPI Backend SHALL return all trading signals within the specified time range
5. WHEN a POST request is made to /backtest/run with parameters (symbol, start_date, end_date, initial_capital), THE FastAPI Backend SHALL execute a backtest and return performance metrics
6. WHEN a POST request is made to /trade/execute with parameters (symbol, signal_type, quantity), THE FastAPI Backend SHALL validate the trade parameters and record the trade execution
7. WHEN a GET request is made to /logs/trades?symbol={symbol}&limit={limit}, THE FastAPI Backend SHALL return the most recent trade records up to the specified limit
8. WHEN any endpoint encounters an error, THE FastAPI Backend SHALL return appropriate HTTP status codes (400 for bad requests, 404 for not found, 500 for server errors) with descriptive error messages

### Requirement 14: React Dashboard User Interface

**User Story:** As a trader, I want a visual dashboard to monitor live data and review trading performance, so that I can make informed decisions and track system behavior.

#### Acceptance Criteria

1. WHEN the React Dashboard loads, THE EATS SHALL display a live price chart with candlesticks and overlaid buy/sell markers for the selected symbol
2. WHEN the React Dashboard loads, THE EATS SHALL display a sentiment dashboard showing the current Sentiment Index, recent sentiment history, and detected events
3. WHEN the React Dashboard loads, THE EATS SHALL display an event summary panel listing recent detected events with timestamps, types, and Event Shock Factors
4. WHEN the React Dashboard loads, THE EATS SHALL display a CMS graph showing the current CMS value and historical CMS trend over the selected time period
5. WHEN the React Dashboard loads, THE EATS SHALL display the current market regime with visual indicator (color-coded: green for Bull, red for Bear, yellow for Sideways, purple for Panic)
6. WHEN a backtest is completed, THE React Dashboard SHALL display backtest results including equity curve, performance metrics table, and trade log
7. WHEN the trade log is displayed, THE React Dashboard SHALL show entry date, entry price, exit date, exit price, PnL, and exit reason for each trade
8. WHEN the React Dashboard displays charts, THE EATS SHALL render price chart with technical indicators (EMA20, EMA50, Bollinger Bands), equity curve, sentiment index timeline, CMS curve, and drawdown curve
9. WHEN live data updates arrive via WebSocket or polling, THE React Dashboard SHALL update all displayed values and charts within 500 milliseconds

### Requirement 15: System Architecture and Deployment

**User Story:** As a DevOps engineer, I want a containerized deployment configuration, so that I can deploy the entire system consistently across environments.

#### Acceptance Criteria

1. WHEN the EATS is deployed, THE system SHALL consist of separate services: PostgreSQL database, Redis server, FastAPI backend, React frontend, and C++ calculation service
2. WHEN Docker Compose is executed, THE EATS SHALL start all services with proper networking, volume mounts, and environment variable configuration
3. WHEN services start, THE EATS SHALL ensure PostgreSQL initializes with the required schema before the backend service attempts database connections
4. WHEN services start, THE EATS SHALL ensure Redis is available before the backend service attempts to publish or subscribe to channels
5. WHEN the system is deployed, THE EATS SHALL expose the FastAPI backend on port 8000 and the React frontend on port 3000
6. WHEN environment variables are provided, THE EATS SHALL configure database connection strings, Redis URLs, API keys, and risk parameters from environment variables rather than hardcoded values

### Requirement 16: Data Parsing and Validation

**User Story:** As a data quality engineer, I want robust input validation and parsing, so that I can ensure data integrity throughout the system.

#### Acceptance Criteria

1. WHEN price data is received, THE EATS SHALL validate that timestamp is in ISO 8601 format, price values are positive numbers, and volume is a non-negative integer
2. WHEN text data is received for sentiment analysis, THE EATS SHALL validate that text length is between 1 and 10000 characters and contains valid UTF-8 encoding
3. WHEN CSV files are uploaded for backtesting, THE EATS SHALL validate file format, check for required columns, and reject files with more than 10% missing data
4. WHEN API requests are received, THE FastAPI Backend SHALL validate request parameters against defined schemas and return 400 Bad Request with detailed error messages for invalid inputs
5. WHEN data validation fails, THE EATS SHALL log the validation error with timestamp, data source, and specific validation rule that failed

### Requirement 17: Logging and Observability

**User Story:** As a system administrator, I want comprehensive logging and monitoring, so that I can troubleshoot issues and monitor system health.

#### Acceptance Criteria

1. WHEN any component performs an operation, THE EATS SHALL log the operation with timestamp, component name, operation type, and execution duration
2. WHEN errors occur, THE EATS SHALL log the error with timestamp, component name, error type, error message, and stack trace
3. WHEN trading signals are generated, THE EATS SHALL log the signal with all triggering conditions and component values for full explainability
4. WHEN backtests complete, THE EATS SHALL log the backtest parameters, execution time, and summary performance metrics
5. WHEN the system starts, THE EATS SHALL log the startup sequence, configuration parameters, and successful initialization of all components

### Requirement 18: Configuration Management

**User Story:** As a system operator, I want configurable parameters for all key system settings, so that I can tune the system without code changes.

#### Acceptance Criteria

1. WHEN the EATS starts, THE system SHALL load configuration from a YAML or JSON file specifying EMA periods, RSI period, MACD parameters, Bollinger Band parameters, ATR period, and CMS weights
2. WHEN the EATS starts, THE system SHALL load trading rule thresholds including sentiment thresholds, CMS thresholds, and regime detection parameters from configuration
3. WHEN the EATS starts, THE system SHALL load risk management parameters including risk_per_trade, maximum_position_size, stop_loss_multiplier, and trailing_stop_multiplier from configuration
4. WHEN configuration parameters are invalid, THE EATS SHALL reject the configuration, log detailed error messages, and refuse to start
5. WHEN configuration is updated, THE EATS SHALL support hot-reloading of parameters without requiring a full system restart for non-critical parameters

### Requirement 19: Pretty Printing and Serialization

**User Story:** As a developer, I want consistent serialization and deserialization of all data structures, so that I can ensure data integrity across system boundaries.

#### Acceptance Criteria

1. WHEN any data structure is serialized to JSON, THE EATS SHALL produce valid JSON with consistent field naming (snake_case) and proper type encoding
2. WHEN JSON data is deserialized, THE EATS SHALL validate the structure against expected schemas and reject malformed data
3. WHEN data structures are serialized and then deserialized, THE EATS SHALL produce an equivalent data structure with all field values preserved
4. WHEN timestamps are serialized, THE EATS SHALL use ISO 8601 format with timezone information
5. WHEN floating-point numbers are serialized, THE EATS SHALL round to 6 decimal places to prevent precision issues

### Requirement 20: Performance and Scalability

**User Story:** As a system architect, I want the system to handle high-frequency data with low latency, so that I can support real-time trading at scale.

#### Acceptance Criteria

1. WHEN processing real-time price updates, THE EATS SHALL complete all calculations (technical indicators, sentiment, CMS, signals) within 200 milliseconds per update
2. WHEN running backtests, THE EATS SHALL process at least 10,000 data points per second using the C++ Acceleration Module
3. WHEN storing data to PostgreSQL, THE EATS SHALL use batch inserts for bulk operations with batch sizes of at least 1000 records
4. WHEN querying historical data, THE EATS SHALL utilize database indexes to return results within 500 milliseconds for queries spanning up to 1 year of data
5. WHEN the system handles multiple concurrent users, THE FastAPI Backend SHALL support at least 100 concurrent requests with response times under 1 second

### Requirement 21: Zerodha Kite Connect Authentication

**User Story:** As a live trader, I want to authenticate with Zerodha Kite Connect API, so that I can execute real trades on NSE and BSE exchanges.

#### Acceptance Criteria

1. WHEN the EATS starts, THE system SHALL initialize KiteConnect client with API key and API secret from environment variables
2. WHEN a user initiates authentication, THE EATS SHALL redirect the user to Zerodha login page and obtain a request token
3. WHEN a request token is received, THE EATS SHALL exchange the request token for an access token using the API secret
4. WHEN an access token is obtained, THE EATS SHALL store the access token securely in PostgreSQL with user identifier and expiration timestamp
5. WHEN an access token expires, THE EATS SHALL detect the expiration and prompt the user to re-authenticate
6. WHEN authentication fails, THE EATS SHALL log the error with timestamp and error details, and return an appropriate error message to the user

### Requirement 22: Zerodha Order Placement and Management

**User Story:** As a live trader, I want to place, modify, and cancel orders through Zerodha, so that I can execute my trading strategy in real markets.

#### Acceptance Criteria

1. WHEN a BUY signal is generated and live trading is enabled, THE EATS SHALL place a market order using kite.place_order() with parameters: exchange, tradingsymbol, transaction_type="BUY", quantity, order_type="MARKET", product type
2. WHEN a SELL signal is generated and live trading is enabled, THE EATS SHALL place a market order with transaction_type="SELL"
3. WHEN an order is placed, THE EATS SHALL receive an order_id from Zerodha and store it in PostgreSQL orders table with timestamp, symbol, order type, quantity, and status
4. WHEN an order needs modification, THE EATS SHALL call kite.modify_order() with order_id and updated parameters (quantity, price, order_type)
5. WHEN an order needs cancellation, THE EATS SHALL call kite.cancel_order() with order_id and update the order status to "CANCELLED" in PostgreSQL
6. WHEN order placement fails, THE EATS SHALL log the error, store the failed order attempt in PostgreSQL, and publish an alert to the Redis alerts channel
7. WHEN an order is successfully placed, THE EATS SHALL publish the order details to the Redis orders channel in JSON format with fields: order_id, symbol, transaction_type, quantity, order_type, status, timestamp

### Requirement 23: Zerodha Position and Holdings Management

**User Story:** As a portfolio manager, I want to fetch current positions and holdings from Zerodha, so that I can track my portfolio state and make informed trading decisions.

#### Acceptance Criteria

1. WHEN the EATS requests position data, THE system SHALL call kite.positions() and retrieve all open positions with fields: tradingsymbol, exchange, quantity, average_price, pnl, product
2. WHEN position data is retrieved, THE EATS SHALL store the positions in PostgreSQL positions table with timestamp and update existing positions if they already exist
3. WHEN the EATS requests holdings data, THE system SHALL call kite.holdings() and retrieve all holdings with fields: tradingsymbol, exchange, quantity, average_price, last_price, pnl
4. WHEN holdings data is retrieved, THE EATS SHALL store the holdings in PostgreSQL holdings table with timestamp
5. WHEN position or holdings data is updated, THE EATS SHALL publish the updated data to Redis positions and holdings channels respectively
6. WHEN position or holdings API calls fail, THE EATS SHALL retry up to 3 times with exponential backoff before logging an error

### Requirement 24: Zerodha Margin and Account Information

**User Story:** As a risk manager, I want to fetch available margin and account balance from Zerodha, so that I can ensure sufficient funds for trading and enforce position sizing limits.

#### Acceptance Criteria

1. WHEN the EATS requests margin data, THE system SHALL call kite.margins() and retrieve margin information including available cash, collateral, and utilized margin
2. WHEN margin data is retrieved, THE EATS SHALL store the margin information in PostgreSQL margins table with timestamp and user identifier
3. WHEN calculating position size for a new trade, THE EATS SHALL verify that available margin is sufficient to cover the required margin for the position
4. WHEN available margin is insufficient for a trade, THE EATS SHALL reject the trade, log the rejection reason, and publish an alert to the Redis alerts channel
5. WHEN margin data is updated, THE EATS SHALL publish the updated margin information to the Redis margins channel

### Requirement 25: Zerodha Real-Time Market Data Integration

**User Story:** As a real-time trader, I want to receive live market data from Zerodha via WebSocket, so that I can generate trading signals based on current market prices.

#### Acceptance Criteria

1. WHEN the EATS starts, THE system SHALL initialize KiteTicker WebSocket client with access token and subscribe to instruments specified in configuration
2. WHEN tick data is received via KiteTicker, THE EATS SHALL extract price, volume, timestamp, and other relevant fields from the tick
3. WHEN tick data is received, THE EATS SHALL publish the data to the Redis price:live channel within 50 milliseconds
4. WHEN tick data is received, THE EATS SHALL trigger technical indicator calculations and signal generation using the updated price data
5. WHEN WebSocket connection is lost, THE EATS SHALL attempt to reconnect automatically with exponential backoff up to 10 retry attempts
6. WHEN WebSocket connection fails after all retries, THE EATS SHALL log a critical error and send an alert notification

### Requirement 26: Zerodha Order Status Tracking

**User Story:** As a trader, I want to track the status of my orders in real-time, so that I can monitor order execution and respond to order updates.

#### Acceptance Criteria

1. WHEN an order is placed, THE EATS SHALL poll kite.order_history(order_id) every 2 seconds until the order reaches a terminal state (COMPLETE, REJECTED, CANCELLED)
2. WHEN order status changes, THE EATS SHALL update the order status in PostgreSQL orders table with the new status and timestamp
3. WHEN an order is filled (status = COMPLETE), THE EATS SHALL record the fill price, fill quantity, and fill timestamp in the trades table
4. WHEN an order is rejected, THE EATS SHALL log the rejection reason and publish an alert to the Redis alerts channel
5. WHEN order status updates are received, THE EATS SHALL publish the updated order status to the Redis order_updates channel

### Requirement 27: Live Trading Safety Controls

**User Story:** As a risk manager, I want safety controls for live trading, so that I can prevent unintended trades and limit potential losses.

#### Acceptance Criteria

1. WHEN the EATS starts, THE system SHALL load a live_trading_enabled flag from configuration that defaults to False
2. WHEN live_trading_enabled is False, THE EATS SHALL generate signals but SHALL NOT place orders with Zerodha
3. WHEN live_trading_enabled is True, THE EATS SHALL enforce a maximum daily loss limit configured in settings
4. WHEN cumulative daily losses exceed the maximum daily loss limit, THE EATS SHALL disable live trading, cancel all open orders, and send a critical alert
5. WHEN live trading is enabled, THE EATS SHALL enforce a maximum number of trades per day configured in settings
6. WHEN the maximum number of trades is reached, THE EATS SHALL stop placing new orders and log a warning message
7. WHEN a trading signal would result in a position size exceeding configured maximum position limits, THE EATS SHALL reject the signal and log the rejection reason
