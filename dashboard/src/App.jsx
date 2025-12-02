import { useState, useEffect } from 'react';
import { api } from './api/client';
import { useWebSocket } from './hooks/useWebSocket';
import CMSGauge from './components/CMSGauge';
import SignalPanel from './components/SignalPanel';
import ExplanationPanel from './components/ExplanationPanel';
import SentimentPanel from './components/SentimentPanel';
import TechnicalIndicatorsPanel from './components/TechnicalIndicatorsPanel';
import MarketRegimePanel from './components/MarketRegimePanel';
import OrderHistoryTable from './components/OrderHistoryTable';
import BacktestInterface from './components/BacktestInterface';

function App() {
  const [currentSignal, setCurrentSignal] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);

  // WebSocket connection for real-time updates
  const { isConnected, error: wsError } = useWebSocket((signalData) => {
    console.log('Received signal update:', signalData);
    setCurrentSignal(signalData);
  });

  // Fetch initial data
  useEffect(() => {
    fetchInitialData();
    
    // Poll for updates every 30 seconds as fallback
    const interval = setInterval(fetchCurrentSignal, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchHealthStatus(),
        fetchCurrentSignal()
      ]);
    } catch (err) {
      console.error('Failed to fetch initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealthStatus = async () => {
    try {
      const health = await api.healthCheck();
      setHealthStatus(health);
    } catch (err) {
      console.error('Health check failed:', err);
    }
  };

  const fetchCurrentSignal = async () => {
    try {
      const signal = await api.getCurrentSignal();
      if (signal) {
        setCurrentSignal(signal);
      }
    } catch (err) {
      console.error('Failed to fetch current signal:', err);
    }
  };

  const getConnectionStatus = () => {
    if (isConnected) {
      return <span className="text-buy">● Connected</span>;
    }
    if (wsError) {
      return <span className="text-sell">● Error</span>;
    }
    return <span className="text-gray-500">● Connecting...</span>;
  };

  const getSystemStatus = () => {
    if (!healthStatus) return <span className="text-gray-500">● Unknown</span>;
    
    const allHealthy = healthStatus.services?.database && 
                       healthStatus.services?.redis && 
                       healthStatus.services?.signal_aggregator;
    
    if (allHealthy) {
      return <span className="text-buy">● Healthy</span>;
    }
    return <span className="text-yellow-500">● Degraded</span>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-semibold text-gray-700 mb-2">Loading Dashboard...</div>
          <div className="text-gray-500">Connecting to trading system</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Explainable Algorithmic Trading
              </h1>
              <p className="text-sm text-gray-500">Real-time trading signals with full transparency</p>
            </div>
            <div className="text-right text-sm">
              <div className="mb-1">
                <span className="text-gray-600">WebSocket: </span>
                {getConnectionStatus()}
              </div>
              <div>
                <span className="text-gray-600">System: </span>
                {getSystemStatus()}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'dashboard'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('orders')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'orders'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Orders
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'backtest'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Backtest
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top Row - CMS Gauge and Signal */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4 text-gray-800">Composite Market Score</h2>
                <CMSGauge score={currentSignal?.cms_score || 0} />
              </div>
              <SignalPanel
                signal={currentSignal?.signal_type}
                confidence={currentSignal?.confidence}
                timestamp={currentSignal?.timestamp}
              />
            </div>

            {/* Explanation Panel */}
            <ExplanationPanel explanation={currentSignal?.explanation} />

            {/* Component Panels */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <SentimentPanel
                sentimentScore={currentSignal?.sentiment_component}
                sentimentDetails={currentSignal?.explanation?.sentiment_details}
              />
              <TechnicalIndicatorsPanel
                technicalScore={currentSignal?.technical_component}
                technicalDetails={currentSignal?.explanation?.technical_details}
              />
              <MarketRegimePanel
                regimeScore={currentSignal?.regime_component}
                regimeDetails={currentSignal?.explanation?.regime_details}
              />
            </div>
          </div>
        )}

        {activeTab === 'orders' && (
          <OrderHistoryTable />
        )}

        {activeTab === 'backtest' && (
          <BacktestInterface />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            Explainable Algorithmic Trading System v1.0.0
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
