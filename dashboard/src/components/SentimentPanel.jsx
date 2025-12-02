const SentimentPanel = ({ sentimentScore, sentimentDetails }) => {
  const getSentimentColor = (score) => {
    if (score > 0.3) return 'text-buy';
    if (score < -0.3) return 'text-sell';
    return 'text-hold';
  };

  const getSentimentLabel = (score) => {
    if (score > 0.6) return 'Very Positive';
    if (score > 0.3) return 'Positive';
    if (score > -0.3) return 'Neutral';
    if (score > -0.6) return 'Negative';
    return 'Very Negative';
  };

  const normalizedScore = sentimentScore !== undefined ? sentimentScore : 0;
  const displayScore = ((normalizedScore + 1) / 2) * 100; // Convert -1 to 1 range to 0 to 100

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Sentiment Analysis</h2>
      
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600">Sentiment Score</span>
          <span className={`text-2xl font-bold ${getSentimentColor(normalizedScore)}`}>
            {normalizedScore.toFixed(2)}
          </span>
        </div>
        
        {/* Sentiment bar */}
        <div className="relative w-full h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`absolute h-full transition-all duration-300 ${
              normalizedScore > 0 ? 'bg-buy' : 'bg-sell'
            }`}
            style={{
              width: `${displayScore}%`,
              left: normalizedScore < 0 ? `${displayScore}%` : '50%',
              right: normalizedScore > 0 ? `${100 - displayScore}%` : '50%'
            }}
          />
          <div className="absolute left-1/2 top-0 w-0.5 h-full bg-gray-400" />
        </div>
        
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Very Negative</span>
          <span>Neutral</span>
          <span>Very Positive</span>
        </div>
      </div>

      <div className="mb-4">
        <div className="inline-block px-3 py-1 rounded-full text-sm font-semibold bg-gray-100">
          {getSentimentLabel(normalizedScore)}
        </div>
      </div>

      {sentimentDetails && (
        <div className="text-sm text-gray-600 border-t pt-3">
          <p>{sentimentDetails}</p>
        </div>
      )}
    </div>
  );
};

export default SentimentPanel;
