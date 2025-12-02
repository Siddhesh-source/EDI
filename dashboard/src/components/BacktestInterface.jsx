import { useState } from 'react';
import { api } from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BacktestInterface = () => {
  const [config, setConfig] = useState({
    symbol: 'RELIANCE',
    start_date: '2024-01-01T00:00:00',
    end_date: '2024-12-01T00:00:00',
    initial_capital: 100000,
    position_size: 0.1,
    cms_buy_threshold: 60,
    cms_sell_threshold: -60,
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: name.includes('threshold') || name.includes('capital') || name === 'position_size'
        ? parseFloat(value)
        : value
    }));
  };

  const runBacktest = async () => {
    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const response = await api.runBacktest(config);
      
      // Fetch the full result
      const fullResult = await api.getBacktestResult(response.backtest_id);
      setResult(fullResult);
    } catch (err) {
      setError(err.message);
      console.error('Backtest failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatEquityCurve = (equityCurve) => {
    if (!equityCurve || equityCurve.length === 0) return [];
    
    return equityCurve.map(([timestamp, value]) => ({
      timestamp: new Date(timestamp).toLocaleDateString(),
      equity: value
    }));
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Backtest Interface</h2>
      
      {/* Configuration Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
          <input
            type="text"
            name="symbol"
            value={config.symbol}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Initial Capital</label>
          <input
            type="number"
            name="initial_capital"
            value={config.initial_capital}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
          <input
            type="datetime-local"
            name="start_date"
            value={config.start_date}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
          <input
            type="datetime-local"
            name="end_date"
            value={config.end_date}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Position Size (0-1)</label>
          <input
            type="number"
            name="position_size"
            value={config.position_size}
            onChange={handleInputChange}
            step="0.01"
            min="0"
            max="1"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CMS Buy Threshold</label>
          <input
            type="number"
            name="cms_buy_threshold"
            value={config.cms_buy_threshold}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CMS Sell Threshold</label>
          <input
            type="number"
            name="cms_sell_threshold"
            value={config.cms_sell_threshold}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <button
        onClick={runBacktest}
        disabled={loading}
        className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {loading ? 'Running Backtest...' : 'Run Backtest'}
      </button>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          Error: {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-6">
          <div className="border-t pt-4">
            <h3 className="text-lg font-semibold mb-3 text-gray-800">Performance Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-600">Total Return</div>
                <div className={`text-xl font-bold ${result.metrics.total_return > 0 ? 'text-buy' : 'text-sell'}`}>
                  {(result.metrics.total_return * 100).toFixed(2)}%
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-600">Sharpe Ratio</div>
                <div className="text-xl font-bold text-gray-800">
                  {result.metrics.sharpe_ratio.toFixed(2)}
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-600">Max Drawdown</div>
                <div className="text-xl font-bold text-sell">
                  {(result.metrics.max_drawdown * 100).toFixed(2)}%
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-600">Win Rate</div>
                <div className="text-xl font-bold text-gray-800">
                  {(result.metrics.win_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-600">Total Trades</div>
                <div className="text-xl font-bold text-gray-800">
                  {result.metrics.total_trades}
                </div>
              </div>
            </div>
          </div>

          {/* Equity Curve */}
          {result.equity_curve && result.equity_curve.length > 0 && (
            <div className="border-t pt-4">
              <h3 className="text-lg font-semibold mb-3 text-gray-800">Equity Curve</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={formatEquityCurve(result.equity_curve)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trade List */}
          {result.trades && result.trades.length > 0 && (
            <div className="border-t pt-4">
              <h3 className="text-lg font-semibold mb-3 text-gray-800">Recent Trades</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Entry</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Exit</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Entry Price</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Exit Price</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {result.trades.slice(0, 10).map((trade, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          {new Date(trade.entry_time).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          {new Date(trade.exit_time).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          ₹{trade.entry_price.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          ₹{trade.exit_price.toFixed(2)}
                        </td>
                        <td className={`px-4 py-2 text-sm font-semibold ${trade.pnl > 0 ? 'text-buy' : 'text-sell'}`}>
                          ₹{trade.pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BacktestInterface;
