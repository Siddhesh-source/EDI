const MarketRegimePanel = ({ regimeScore, regimeDetails }) => {
  const parseRegime = (details) => {
    if (!details) return { type: 'Unknown', confidence: 0 };
    
    const regimeTypes = ['trending-up', 'trending-down', 'ranging', 'volatile', 'calm'];
    const foundType = regimeTypes.find(type => 
      details.toLowerCase().includes(type.replace('-', ' '))
    );
    
    const confidenceMatch = details.match(/confidence[:\s]+(\d+\.?\d*)%?/i);
    const confidence = confidenceMatch ? parseFloat(confidenceMatch[1]) : 0;
    
    return {
      type: foundType || 'Unknown',
      confidence: confidence > 1 ? confidence : confidence * 100
    };
  };

  const regime = parseRegime(regimeDetails);

  const getRegimeColor = (type) => {
    switch (type.toLowerCase()) {
      case 'trending-up':
        return 'bg-buy text-white';
      case 'trending-down':
        return 'bg-sell text-white';
      case 'ranging':
        return 'bg-hold text-white';
      case 'volatile':
        return 'bg-orange-500 text-white';
      case 'calm':
        return 'bg-blue-500 text-white';
      default:
        return 'bg-gray-400 text-white';
    }
  };

  const getRegimeIcon = (type) => {
    switch (type.toLowerCase()) {
      case 'trending-up':
        return '📈';
      case 'trending-down':
        return '📉';
      case 'ranging':
        return '↔️';
      case 'volatile':
        return '⚡';
      case 'calm':
        return '😌';
      default:
        return '❓';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Market Regime</h2>
      
      <div className="mb-4">
        <div className={`${getRegimeColor(regime.type)} rounded-lg px-4 py-3 text-center`}>
          <div className="text-3xl mb-1">{getRegimeIcon(regime.type)}</div>
          <div className="text-lg font-bold capitalize">
            {regime.type.replace('-', ' ')}
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600">Regime Score</span>
          <span className="text-xl font-bold text-gray-800">
            {(regimeScore || 0).toFixed(2)}
          </span>
        </div>
        
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600">Confidence</span>
          <span className="text-xl font-bold text-gray-800">
            {regime.confidence.toFixed(1)}%
          </span>
        </div>

        {/* Confidence bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${regime.confidence}%` }}
          />
        </div>
      </div>

      {regimeDetails && (
        <div className="text-sm text-gray-600 border-t pt-3">
          <p>{regimeDetails}</p>
        </div>
      )}

      {/* Regime descriptions */}
      <div className="mt-4 text-xs text-gray-500 space-y-1">
        <p><strong>Trending Up:</strong> Strong upward price movement</p>
        <p><strong>Trending Down:</strong> Strong downward price movement</p>
        <p><strong>Ranging:</strong> Price moving sideways in a range</p>
        <p><strong>Volatile:</strong> High price fluctuations</p>
        <p><strong>Calm:</strong> Low volatility, stable prices</p>
      </div>
    </div>
  );
};

export default MarketRegimePanel;
