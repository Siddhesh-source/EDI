import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const CMSGauge = ({ score }) => {
  // Normalize score from -100 to 100 range to 0 to 100 for display
  const normalizedScore = ((score + 100) / 200) * 100;
  
  // Determine color based on score
  const getColor = (score) => {
    if (score > 60) return '#10b981'; // Green for positive
    if (score < -60) return '#ef4444'; // Red for negative
    return '#6b7280'; // Gray for neutral
  };

  const color = getColor(score);

  // Create gauge data
  const data = [
    { value: normalizedScore, fill: color },
    { value: 100 - normalizedScore, fill: '#e5e7eb' }
  ];

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-64 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius={60}
              outerRadius={80}
              paddingAngle={0}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        
        {/* Score display in center */}
        <div className="absolute inset-0 flex items-end justify-center pb-2">
          <div className="text-center">
            <div className="text-4xl font-bold" style={{ color }}>
              {score.toFixed(1)}
            </div>
            <div className="text-sm text-gray-500">CMS Score</div>
          </div>
        </div>
      </div>

      {/* Scale markers */}
      <div className="w-64 flex justify-between text-xs text-gray-500 mt-2">
        <span>-100</span>
        <span>-60</span>
        <span>0</span>
        <span>60</span>
        <span>100</span>
      </div>
    </div>
  );
};

export default CMSGauge;
