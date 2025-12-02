const TechnicalIndicatorsPanel = ({ technicalScore, technicalDetails }) => {
  const getIndicatorStatus = (score) => {
    if (score > 0.3) return { label: 'Bullish', color: 'text-buy' };
    if (score < -0.3) return { label: 'Bearish', color: 'text-sell' };
    return { label: 'Neutral', color: 'text-hold' };
  };

  const status = getIndicatorStatus(technicalScore || 0);

  // Parse technical details to extract individual indicators
  const parseIndicators = (details) => {
    if (!details) return [];
    
    const indicators = [];
    const patterns = [
      { name: 'RSI', regex: /RSI[:\s]+(\d+\.?\d*)/i },
      { name: 'MACD', regex: /MACD[:\s]+([-]?\d+\.?\d*)/i },
      { name: 'Bollinger Bands', regex: /Bollinger[:\s]+(\w+)/i },
      { name: 'SMA 20', regex: /SMA[:\s]*20[:\s]+(\d+\.?\d*)/i },
      { name: 'SMA 50', regex: /SMA[:\s]*50[:\s]+(\d+\.?\d*)/i },
    ];

    patterns.forEach(({ name, regex }) => {
      const match = details.match(regex);
      if (match) {
        indicators.push({ name, value: match[1] });
      }
    });

    return indicators;
  };

  const indicators = parseIndicators(technicalDetails);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Technical Indicators</h2>
      
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600">Technical Score</span>
          <span className={`text-2xl font-bold ${status.color}`}>
            {(technicalScore || 0).toFixed(2)}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                technicalScore > 0 ? 'bg-buy' : technicalScore < 0 ? 'bg-sell' : 'bg-hold'
              }`}
              style={{ width: `${Math.abs(technicalScore || 0) * 100}%` }}
            />
          </div>
          <span className={`text-sm font-semibold ${status.color}`}>
            {status.label}
          </span>
        </div>
      </div>

      {indicators.length > 0 && (
        <div className="space-y-2 mb-4">
          <h3 className="text-sm font-semibold text-gray-700">Indicator Values</h3>
          {indicators.map((indicator, index) => (
            <div key={index} className="flex justify-between text-sm">
              <span className="text-gray-600">{indicator.name}:</span>
              <span className="font-semibold">{indicator.value}</span>
            </div>
          ))}
        </div>
      )}

      {technicalDetails && (
        <div className="text-sm text-gray-600 border-t pt-3">
          <p>{technicalDetails}</p>
        </div>
      )}
    </div>
  );
};

export default TechnicalIndicatorsPanel;
