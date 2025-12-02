# Trading Dashboard

React-based dashboard for the Explainable Algorithmic Trading System.

## Features

- **Real-time Updates**: WebSocket connection for live trading signals
- **CMS Gauge**: Visual representation of Composite Market Score (-100 to +100)
- **Signal Panel**: Current trading signal (BUY/SELL/HOLD) with confidence
- **Explanation Panel**: Detailed breakdown of signal components
- **Sentiment Panel**: News sentiment analysis visualization
- **Technical Indicators Panel**: Technical analysis signals and values
- **Market Regime Panel**: Current market regime classification
- **Order History**: Table of executed orders with filtering
- **Backtest Interface**: Run and visualize backtests

## Technology Stack

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Recharts**: Charting library for data visualization
- **Axios**: HTTP client for REST API calls
- **WebSocket**: Real-time communication

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Update `.env` with your API configuration:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_API_KEY=your-api-key-here
```

## Development

Start the development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Build

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Project Structure

```
dashboard/
├── src/
│   ├── api/
│   │   └── client.js          # API client with axios
│   ├── components/
│   │   ├── CMSGauge.jsx       # CMS gauge visualization
│   │   ├── SignalPanel.jsx    # Current signal display
│   │   ├── ExplanationPanel.jsx # Signal explanation
│   │   ├── SentimentPanel.jsx # Sentiment visualization
│   │   ├── TechnicalIndicatorsPanel.jsx # Technical indicators
│   │   ├── MarketRegimePanel.jsx # Market regime display
│   │   ├── OrderHistoryTable.jsx # Order history table
│   │   └── BacktestInterface.jsx # Backtesting interface
│   ├── hooks/
│   │   └── useWebSocket.js    # WebSocket hook
│   ├── App.jsx                # Main application component
│   ├── main.jsx               # Application entry point
│   └── index.css              # Global styles
├── public/                    # Static assets
├── index.html                 # HTML template
├── vite.config.js            # Vite configuration
├── tailwind.config.js        # Tailwind CSS configuration
└── package.json              # Dependencies and scripts
```

## API Integration

The dashboard connects to the FastAPI backend at the configured `VITE_API_URL`.

### REST API Endpoints

- `GET /health` - Health check
- `GET /api/v1/signal/current` - Get current trading signal
- `GET /api/v1/signal/history` - Get signal history
- `POST /api/v1/backtest` - Run backtest
- `GET /api/v1/backtest/{id}` - Get backtest results
- `GET /api/v1/orders` - Get order history

### WebSocket

- `WS /ws/signals` - Real-time signal updates

## Components

### CMSGauge
Displays the Composite Market Score as a gauge chart with color coding:
- Green: Positive score (> 60)
- Red: Negative score (< -60)
- Gray: Neutral score (-60 to 60)

### SignalPanel
Shows the current trading signal with:
- Signal type (BUY/SELL/HOLD)
- Confidence level
- Timestamp

### ExplanationPanel
Provides detailed explanation including:
- Summary
- Component scores breakdown
- Sentiment details
- Technical indicator details
- Market regime details
- Event details

### SentimentPanel
Visualizes sentiment analysis:
- Sentiment score (-1 to +1)
- Visual bar representation
- Sentiment label (Very Positive to Very Negative)

### TechnicalIndicatorsPanel
Displays technical analysis:
- Technical score
- Bullish/Bearish/Neutral status
- Individual indicator values (RSI, MACD, etc.)

### MarketRegimePanel
Shows market regime classification:
- Regime type (Trending Up/Down, Ranging, Volatile, Calm)
- Confidence level
- Visual representation

### OrderHistoryTable
Lists executed orders with:
- Order ID, symbol, side, type
- Quantity, price, status
- Timestamp
- Filtering by status

### BacktestInterface
Allows running backtests with:
- Configuration form
- Performance metrics display
- Equity curve chart
- Trade list

## Color Scheme

- **Buy/Positive**: Green (#10b981)
- **Sell/Negative**: Red (#ef4444)
- **Hold/Neutral**: Gray (#6b7280)
- **Primary**: Blue (#3b82f6)

## Requirements Validation

This dashboard satisfies the following requirements:

- **Requirement 10.1**: WebSocket connection for real-time updates
- **Requirement 10.2**: Display signals within 1 second of generation
- **Requirement 10.3**: CMS gauge with color coding (green/red)
- **Requirement 10.4**: Separate panels for sentiment, technical, and regime
- **Requirement 10.5**: Historical signal retrieval and display
- **Requirement 14.5**: Structured, human-readable explanations

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

Part of the Explainable Algorithmic Trading System
