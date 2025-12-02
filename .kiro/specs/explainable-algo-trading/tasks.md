# Implementation Plan

- [x] 1. Set up project structure and infrastructure





  - Create directory structure for all modules (sentiment, events, indicators, regime, signal, backtest, executor)
  - Set up Python virtual environment and install dependencies (FastAPI, Redis, PostgreSQL, Hypothesis, pytest)
  - Configure Docker Compose for Redis and PostgreSQL
  - Create shared data models and type definitions
  - Set up logging configuration
  - _Requirements: All requirements depend on proper project structure_

- [x] 2. Implement PostgreSQL database schema and connection management




  - Create database schema with all tables (prices, articles, sentiment_scores, events, trading_signals, orders, backtest_results)
  - Implement database connection pooling
  - Create database migration scripts
  - Implement base repository pattern for data access
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 2.1 Write property test for database record completeness
  - **Property 24: Database record completeness**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [x] 3. Implement Redis pub/sub pipeline






  - Set up Redis connection with connection pooling
  - Create publisher interface for all data types
  - Create subscriber interface with channel management
  - Implement reconnection logic with exponential backoff
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ]* 3.1 Write property test for Redis channel separation
  - **Property 22: Redis channel separation**
  - **Validates: Requirements 7.2**

- [ ]* 3.2 Write property test for Redis subscription delivery
  - **Property 23: Redis subscription delivery**
  - **Validates: Requirements 7.3**

- [x] 4. Implement NewsAPI sentiment analyzer



  - Create NewsAPI client for fetching articles
  - Implement rule-based sentiment analysis with keyword dictionaries
  - Add negation handling for sentiment analysis
  - Implement concurrent article processing
  - Publish sentiment scores to Redis sentiment channel
  - Store articles and sentiment scores in PostgreSQL
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ]* 4.1 Write property test for sentiment score bounds
  - **Property 1: Sentiment score bounds invariant**
  - **Validates: Requirements 1.2**

- [ ]* 4.2 Write property test for sentiment publishing completeness
  - **Property 2: Sentiment publishing completeness**
  - **Validates: Requirements 1.3**

- [ ]* 4.3 Write property test for concurrent article processing
  - **Property 3: Concurrent article processing**
  - **Validates: Requirements 1.4**

- [x] 5. Implement event detector





  - Create keyword dictionary for event types (earnings, merger, acquisition, bankruptcy, regulatory, etc.)
  - Implement event classification logic
  - Implement severity scoring algorithm
  - Publish high-priority events to Redis events channel
  - Store events in PostgreSQL
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 5.1 Write property test for event severity bounds
  - **Property 4: Event severity bounds invariant**
  - **Validates: Requirements 2.2**

- [ ]* 5.2 Write property test for high-severity event alerting
  - **Property 5: High-severity event alerting**
  - **Validates: Requirements 2.3**

- [ ]* 5.3 Write property test for multiple event detection
  - **Property 6: Multiple event detection**
  - **Validates: Requirements 2.4**


- [x] 6. Implement C++ Technical Indicator Engine



  - Set up C++ project with CMake build system
  - Implement RSI calculation
  - Implement MACD calculation
  - Implement Bollinger Bands calculation
  - Implement SMA and EMA calculations
  - Implement ATR calculation
  - Create Python bindings using pybind11
  - Implement signal generation based on threshold crossings
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ]* 6.1 Write property test for technical indicator publishing
  - **Property 7: Technical indicator publishing**
  - **Validates: Requirements 3.2**

- [ ]* 6.2 Write property test for technical signal generation
  - **Property 8: Technical signal generation on threshold crossing**
  - **Validates: Requirements 3.3**

- [ ]* 6.3 Write property test for historical indicator computation
  - **Property 9: Historical indicator computation completeness**
  - **Validates: Requirements 3.4**

- [ ]* 6.4 Write property test for C++ data format acceptance
  - **Property 34: C++ engine data format acceptance**
  - **Validates: Requirements 12.2**

- [ ]* 6.5 Write property test for C++ output format
  - **Property 35: C++ engine output format**
  - **Validates: Requirements 12.3**

- [x] 7. Implement market regime detector





  - Implement regime classification algorithm (trending-up, trending-down, ranging, volatile, calm)
  - Implement confidence scoring
  - Implement rolling window analysis (100 bars)
  - Publish regime changes to Redis regime channel
  - Store regime data in PostgreSQL
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 7.1 Write property test for regime classification validity
  - **Property 10: Regime classification validity**
  - **Validates: Requirements 4.1**

- [ ]* 7.2 Write property test for regime confidence bounds
  - **Property 11: Regime confidence bounds invariant**
  - **Validates: Requirements 4.2**

- [ ]* 7.3 Write property test for regime change publishing
  - **Property 12: Regime change publishing**
  - **Validates: Requirements 4.3**

- [ ]* 7.4 Write property test for regime detection window size
  - **Property 13: Regime detection window size**
  - **Validates: Requirements 4.4**

- [ ]* 7.5 Write property test for low-confidence regime default
  - **Property 14: Low-confidence regime default**
  - **Validates: Requirements 4.5**

- [x] 8. Implement signal aggregator and CMS computation





  - Subscribe to all Redis channels (sentiment, events, indicators, regime)
  - Implement data aggregation logic
  - Implement CMS computation with configurable weights
  - Implement signal generation rules (BUY > 60, SELL < -60, HOLD otherwise)
  - Create detailed explanation generation
  - Publish signals to Redis signals channel
  - Store signals in PostgreSQL
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 14.1, 14.2, 14.3, 14.4_

- [ ]* 8.1 Write property test for CMS bounds
  - **Property 15: CMS bounds invariant**
  - **Validates: Requirements 5.2**

- [ ]* 8.2 Write property test for CMS signal generation rules
  - **Property 16: CMS signal generation rules**
  - **Validates: Requirements 5.3, 5.4, 5.5**

- [ ]* 8.3 Write property test for signal explanation completeness
  - **Property 17: Signal explanation completeness**
  - **Validates: Requirements 5.6, 14.1, 14.2**

- [ ]* 8.4 Write property test for technical indicator explanation detail
  - **Property 37: Technical indicator explanation detail**
  - **Validates: Requirements 14.3**

- [ ]* 8.5 Write property test for event explanation completeness
  - **Property 38: Event explanation completeness**
  - **Validates: Requirements 14.4**
-

- [x] 9. Checkpoint - Ensure all core data pipeline tests pass



  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement backtesting module




  - Create backtest configuration interface
  - Implement historical data retrieval from PostgreSQL
  - Implement chronological data replay without look-ahead bias
  - Implement trade simulation logic
  - Compute performance metrics (total return, Sharpe ratio, max drawdown, win rate)
  - Generate trade records with entry/exit details
  - Store backtest results in PostgreSQL
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 10.1 Write property test for backtest chronological replay
  - **Property 18: Backtest chronological replay**
  - **Validates: Requirements 6.2**

- [ ]* 10.2 Write property test for backtest metrics completeness
  - **Property 19: Backtest metrics completeness**
  - **Validates: Requirements 6.3**

- [ ]* 10.3 Write property test for backtest trade record completeness
  - **Property 20: Backtest trade record completeness**
  - **Validates: Requirements 6.4**

- [ ]* 10.4 Write property test for backtest result persistence
  - **Property 21: Backtest result persistence**
  - **Validates: Requirements 6.5**

- [x] 11. Implement order executor with Kite Connect integration






  - Create Kite Connect API client
  - Implement signal validation against risk management rules
  - Implement order submission logic
  - Implement order status tracking
  - Handle order fill notifications
  - Store orders in PostgreSQL
  - Implement error handling for API failures
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ]* 11.1 Write property test for order validation
  - **Property 30: Order validation before execution**
  - **Validates: Requirements 11.1**

- [ ]* 11.2 Write property test for order submission completeness
  - **Property 31: Order submission completeness**
  - **Validates: Requirements 11.2**

- [ ]* 11.3 Write property test for order confirmation persistence
  - **Property 32: Order confirmation persistence**
  - **Validates: Requirements 11.3**

- [ ]* 11.4 Write property test for order status update on fill
  - **Property 33: Order status update on fill**
  - **Validates: Requirements 11.4**

- [x] 12. Implement FastAPI backend





  - Create FastAPI application with middleware (CORS, authentication, logging)
  - Implement health check endpoint
  - Implement current signal endpoint
  - Implement signal history endpoint
  - Implement backtest endpoints (POST /backtest, GET /backtest/{id})
  - Implement orders endpoint
  - Implement WebSocket endpoint for real-time updates
  - Initialize connections to Redis, PostgreSQL, and C++ engine on startup
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 12.1 Write property test for API authentication enforcement
  - **Property 25: API authentication enforcement**
  - **Validates: Requirements 9.1**

- [ ]* 12.2 Write property test for backtest request delegation
  - **Property 26: Backtest request delegation**
  - **Validates: Requirements 9.4**

- [ ]* 12.3 Write property test for API error response format
  - **Property 27: API error response format**
  - **Validates: Requirements 9.5**

- [x] 13. Implement React dashboard





  - Set up React project with Tailwind CSS
  - Create CMS gauge component with color coding
  - Create signal panel component
  - Create explanation panel component
  - Create sentiment panel component
  - Create technical indicators panel component
  - Create market regime panel component
  - Create order history table component
  - Create backtest interface component
  - Implement WebSocket connection for real-time updates
  - Implement REST API client for historical data
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 14.5_

- [ ]* 13.1 Write property test for dashboard CMS visualization
  - **Property 28: Dashboard CMS visualization**
  - **Validates: Requirements 10.3**

- [ ]* 13.2 Write property test for dashboard component panel separation
  - **Property 29: Dashboard component panel separation**
  - **Validates: Requirements 10.4**

- [x] 14. Implement comprehensive error handling





  - Implement error logging with structured format
  - Implement graceful degradation for NewsAPI unavailability
  - Implement Redis reconnection with buffering
  - Implement PostgreSQL retry logic with queuing
  - Implement Kite Connect API failure handling
  - Add circuit breaker patterns for external services
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ]* 14.1 Write property test for error logging completeness
  - **Property 36: Error logging completeness**
  - **Validates: Requirements 13.1**

- [ ] 15. Final checkpoint - Integration testing and system validation
  - Ensure all tests pass, ask the user if questions arise.