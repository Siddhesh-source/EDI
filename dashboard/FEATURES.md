# Dashboard Features

## Overview
The React dashboard provides a comprehensive, real-time interface for monitoring and interacting with the Explainable Algorithmic Trading System.

## Core Features

### 1. Real-time Signal Monitoring
- **WebSocket Connection**: Live updates from the trading system
- **Automatic Reconnection**: Exponential backoff with up to 5 retry attempts
- **Connection Status**: Visual indicator showing connection health
- **Fallback Polling**: 30-second polling as backup to WebSocket

### 2. Composite Market Score (CMS) Visualization
- **Gauge Chart**: Semi-circular gauge showing CMS from -100 to +100
- **Color Coding**: 
  - Green for bullish (> 60)
  - Red for bearish (< -60)
  - Gray for neutral (-60 to 60)
- **Scale Markers**: Clear visual reference points

### 3. Signal Panel
- **Current Signal**: Large, prominent display of BUY/SELL/HOLD
- **Signal Icons**: Visual indicators (↑ for buy, ↓ for sell, → for hold)
- **Confidence Level**: Percentage confidence in the signal
- **Timestamp**: When the signal was generated

### 4. Explanation Panel
- **Summary**: High-level explanation of the signal
- **Component Scores**: Visual breakdown of sentiment, technical, and regime scores
- **Detailed Explanations**: Separate sections for:
  - Sentiment analysis details
  - Technical indicator details
  - Market regime details
  - Event details
- **Color-coded Borders**: Visual hierarchy for different components

### 5. Sentiment Analysis Panel
- **Sentiment Score**: Numerical score from -1 to +1
- **Visual Bar**: Gradient bar showing sentiment intensity
- **Sentiment Label**: Text description (Very Positive to Very Negative)
- **Details**: Explanation of sentiment analysis

### 6. Technical Indicators Panel
- **Technical Score**: Aggregated technical signal strength
- **Status Indicator**: Bullish/Bearish/Neutral classification
- **Individual Indicators**: Parsed values for RSI, MACD, Bollinger Bands, etc.
- **Progress Bar**: Visual representation of technical strength

### 7. Market Regime Panel
- **Regime Type**: Classification (Trending Up/Down, Ranging, Volatile, Calm)
- **Regime Icons**: Emoji indicators for each regime type
- **Confidence Level**: Percentage confidence in regime classification
- **Confidence Bar**: Visual representation
- **Regime Descriptions**: Educational tooltips

### 8. Order History Table
- **Order List**: Comprehensive table of all orders
- **Filtering**: Filter by status (All, Filled, Pending)
- **Order Details**: ID, symbol, side, type, quantity, price, status, timestamp
- **Color Coding**: 
  - Green for filled orders
  - Blue for pending/submitted
  - Red for rejected
  - Gray for cancelled
- **Refresh**: Manual refresh capability

### 9. Backtest Interface
- **Configuration Form**: 
  - Symbol selection
  - Date range picker
  - Initial capital
  - Position size
  - CMS thresholds
- **Performance Metrics**:
  - Total return
  - Sharpe ratio
  - Maximum drawdown
  - Win rate
  - Total trades
- **Equity Curve**: Line chart showing portfolio value over time
- **Trade List**: Detailed list of all trades with P&L
- **Visual Results**: Color-coded metrics (green for positive, red for negative)

### 10. Navigation
- **Tab-based Navigation**: Easy switching between Dashboard, Orders, and Backtest
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Persistent State**: Maintains state across tab switches

### 11. System Health Monitoring
- **Health Status**: Real-time system health indicator
- **Service Status**: Individual status for database, Redis, and signal aggregator
- **Connection Status**: WebSocket connection indicator

## User Experience Features

### Visual Design
- **Clean Interface**: Minimalist design focusing on data
- **Consistent Color Scheme**: Unified color palette throughout
- **Responsive Layout**: Grid-based layout that adapts to screen size
- **Card-based Components**: Organized information in distinct cards
- **Shadow Effects**: Subtle shadows for depth and hierarchy

### Interactivity
- **Hover Effects**: Visual feedback on interactive elements
- **Loading States**: Clear indication when data is loading
- **Error Messages**: User-friendly error messages
- **Form Validation**: Client-side validation for backtest configuration

### Performance
- **Optimized Rendering**: React hooks for efficient updates
- **Lazy Loading**: Components load only when needed
- **Debounced Updates**: Prevents excessive re-renders
- **Efficient Charts**: Recharts optimized for performance

## Technical Features

### API Integration
- **REST Client**: Axios-based client with interceptors
- **Request Logging**: Console logging for debugging
- **Error Handling**: Comprehensive error handling and user feedback
- **Authentication**: API key authentication via headers

### WebSocket Management
- **Custom Hook**: Reusable `useWebSocket` hook
- **Automatic Reconnection**: Exponential backoff strategy
- **Keep-alive**: Ping/pong mechanism
- **Connection Lifecycle**: Proper cleanup on unmount

### State Management
- **React Hooks**: useState and useEffect for local state
- **Prop Drilling**: Minimal prop drilling with component composition
- **Derived State**: Computed values from props

### Build System
- **Vite**: Fast build tool with HMR
- **Environment Variables**: Runtime configuration via .env
- **Production Build**: Optimized production bundle
- **Code Splitting**: Automatic code splitting

## Accessibility

- **Semantic HTML**: Proper HTML5 semantic elements
- **Color Contrast**: WCAG AA compliant color contrast
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: ARIA labels where needed

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Future Enhancement Opportunities

1. **Advanced Filtering**: More sophisticated filtering options
2. **Custom Alerts**: User-configurable alerts
3. **Historical Charts**: Price charts with indicator overlays
4. **Export Functionality**: CSV/PDF export
5. **Dark Mode**: Theme toggle
6. **Multi-Symbol Support**: Track multiple symbols simultaneously
7. **Performance Analytics**: Detailed performance tracking
8. **Mobile App**: React Native mobile application
9. **Notifications**: Browser push notifications
10. **User Preferences**: Customizable dashboard layout
