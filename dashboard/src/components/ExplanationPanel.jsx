const ExplanationPanel = ({ explanation }) => {
  if (!explanation) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Signal Explanation</h2>
        <p className="text-gray-500">No explanation available</p>
      </div>
    );
  }

  const componentScores = explanation.component_scores || {};

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Signal Explanation</h2>
      
      {/* Summary */}
      {explanation.summary && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-1">Summary</h3>
          <p className="text-sm text-blue-800">{explanation.summary}</p>
        </div>
      )}

      {/* Component Scores */}
      {Object.keys(componentScores).length > 0 && (
        <div className="mb-4">
          <h3 className="font-semibold text-gray-700 mb-2">Component Scores</h3>
          <div className="space-y-2">
            {Object.entries(componentScores).map(([key, value]) => (
              <div key={key} className="flex items-center">
                <span className="text-sm text-gray-600 w-32 capitalize">
                  {key.replace('_', ' ')}:
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                  <div
                    className={`h-2 rounded-full ${
                      value > 0 ? 'bg-buy' : value < 0 ? 'bg-sell' : 'bg-hold'
                    }`}
                    style={{ width: `${Math.abs(value) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-semibold w-16 text-right">
                  {(value * 100).toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Explanations */}
      <div className="space-y-3">
        {explanation.sentiment_details && (
          <div className="border-l-4 border-purple-500 pl-3">
            <h4 className="font-semibold text-sm text-gray-700">Sentiment Analysis</h4>
            <p className="text-sm text-gray-600">{explanation.sentiment_details}</p>
          </div>
        )}

        {explanation.technical_details && (
          <div className="border-l-4 border-blue-500 pl-3">
            <h4 className="font-semibold text-sm text-gray-700">Technical Indicators</h4>
            <p className="text-sm text-gray-600">{explanation.technical_details}</p>
          </div>
        )}

        {explanation.regime_details && (
          <div className="border-l-4 border-green-500 pl-3">
            <h4 className="font-semibold text-sm text-gray-700">Market Regime</h4>
            <p className="text-sm text-gray-600">{explanation.regime_details}</p>
          </div>
        )}

        {explanation.event_details && (
          <div className="border-l-4 border-red-500 pl-3">
            <h4 className="font-semibold text-sm text-gray-700">Market Events</h4>
            <p className="text-sm text-gray-600">{explanation.event_details}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExplanationPanel;
