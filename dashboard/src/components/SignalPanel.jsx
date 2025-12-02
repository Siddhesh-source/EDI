const SignalPanel = ({ signal, confidence, timestamp }) => {
  const getSignalColor = (signal) => {
    switch (signal?.toLowerCase()) {
      case 'buy':
        return 'bg-buy text-white';
      case 'sell':
        return 'bg-sell text-white';
      case 'hold':
        return 'bg-hold text-white';
      default:
        return 'bg-gray-300 text-gray-700';
    }
  };

  const getSignalIcon = (signal) => {
    switch (signal?.toLowerCase()) {
      case 'buy':
        return '↑';
      case 'sell':
        return '↓';
      case 'hold':
        return '→';
      default:
        return '?';
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    const date = new Date(ts);
    return date.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Current Signal</h2>
      
      <div className="flex items-center justify-center mb-4">
        <div className={`${getSignalColor(signal)} rounded-full px-8 py-4 text-3xl font-bold flex items-center gap-3`}>
          <span className="text-4xl">{getSignalIcon(signal)}</span>
          <span>{signal?.toUpperCase() || 'N/A'}</span>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Confidence:</span>
          <span className="font-semibold">{confidence ? `${(confidence * 100).toFixed(1)}%` : 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Updated:</span>
          <span className="font-semibold">{formatTimestamp(timestamp)}</span>
        </div>
      </div>
    </div>
  );
};

export default SignalPanel;
