import React from 'react';

export interface ForecastPoint {
  horizon: number;
  target_year: number;
  target_week: number;
  district_name?: string;
  province?: string;
  population?: number;
  piped_water_pct?: number;
  pred_median: number;
  q025: number;
  q25: number;
  q75: number;
  q975: number;
  threshold_q95: number;
  risk_tier: string;
  incidence_per_100k: number;
  exceed_prob: number;
  early_anomaly?: boolean;
}

interface FanChartProps {
  districtName: string;
  forecasts: ForecastPoint[];
  recentHistory?: { week: number; cases: number }[];
  cutoffWeekStr: string;
}

export const FanChart: React.FC<FanChartProps> = ({
  districtName,
  forecasts,
  recentHistory = [],
  cutoffWeekStr,
}) => {
  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center bg-slate-900/50 rounded-xl border border-slate-800 text-slate-400">
        No forecast points available for {districtName}.
      </div>
    );
  }

  // Calculate scales for SVG coordinates
  // SVG viewBox: 0 0 600 240
  const width = 600;
  const height = 240;
  const padding = { top: 20, right: 40, bottom: 40, left: 55 };

  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  // Maximum value across 95% band and historical threshold
  const maxForecastVal = Math.max(...forecasts.map((f) => f.q975));
  const maxHistVal = recentHistory.length > 0 ? Math.max(...recentHistory.map((h) => h.cases)) : 0;
  const thresholdVal = forecasts[0]?.threshold_q95 || 50;

  const yMax = Math.max(10, Math.ceil(Math.max(maxForecastVal, maxHistVal, thresholdVal * 1.15) * 1.15));

  const scaleY = (val: number) => {
    const clamped = Math.max(0, Math.min(yMax, val));
    return padding.top + plotH - (clamped / yMax) * plotH;
  };

  // Combine recent history points (4 weeks prior) + 4 forecast horizons
  // Total steps = history (say 4) + 4 = 8 steps
  const histPoints = recentHistory.slice(-4);
  const totalSteps = histPoints.length + forecasts.length;

  const getStepX = (stepIndex: number) => {
    return padding.left + (stepIndex / (totalSteps - 1 || 1)) * plotW;
  };

  // X coords:
  // History steps: 0 .. histPoints.length - 1
  // Forecast steps: histPoints.length .. totalSteps - 1
  const histCoords = histPoints.map((h, i) => ({
    x: getStepX(i),
    y: scaleY(h.cases),
    label: `W${h.week}`,
    cases: h.cases,
  }));

  const originX = histPoints.length > 0 ? getStepX(histPoints.length - 1) : padding.left;
  const originY = histPoints.length > 0 ? scaleY(histPoints[histPoints.length - 1].cases) : scaleY(forecasts[0].pred_median);

  const forecastCoords = forecasts.map((f, i) => {
    const stepIdx = histPoints.length + i;
    return {
      x: getStepX(stepIdx),
      yMedian: scaleY(f.pred_median),
      yQ025: scaleY(f.q025),
      yQ25: scaleY(f.q25),
      yQ75: scaleY(f.q75),
      yQ975: scaleY(f.q975),
      label: `+${f.horizon}W (W${f.target_week})`,
      data: f,
    };
  });

  // Construct SVG polygon path for 95% prediction interval band
  const band95Path = [
    `M ${originX} ${originY}`,
    ...forecastCoords.map((c) => `L ${c.x} ${c.yQ975}`),
    ...[...forecastCoords].reverse().map((c) => `L ${c.x} ${c.yQ025}`),
    `Z`,
  ].join(' ');

  // Construct SVG polygon path for 50% prediction interval band (IQR)
  const band50Path = [
    `M ${originX} ${originY}`,
    ...forecastCoords.map((c) => `L ${c.x} ${c.yQ75}`),
    ...[...forecastCoords].reverse().map((c) => `L ${c.x} ${c.yQ25}`),
    `Z`,
  ].join(' ');

  // Trajectory line for median
  const medianLinePath = [
    `M ${originX} ${originY}`,
    ...forecastCoords.map((c) => `L ${c.x} ${c.yMedian}`),
  ].join(' ');

  // Historical trajectory line
  const histLinePath = histCoords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');

  const thresholdY = scaleY(thresholdVal);

  return (
    <div className="w-full bg-slate-900/90 rounded-2xl border border-slate-800 p-4 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h4 className="text-base font-bold text-white flex items-center gap-2">
            <span>{districtName} 4-Week Predictive Fan Chart</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
              Cutoff: {cutoffWeekStr}
            </span>
          </h4>
          <p className="text-xs text-slate-400">
            Solid line = Predicted Median; Inner band = 50% IQR; Outer band = 95% Confidence Interval
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded bg-sky-500/25 border border-sky-400/40"></span>
            <span className="text-slate-300">95% CI</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded bg-sky-500/50 border border-sky-400"></span>
            <span className="text-slate-300">50% IQR</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-rose-500 stroke-dashed border-b border-rose-500"></span>
            <span className="text-rose-300">95th %ile Threshold</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto min-w-[500px]">
          {/* Horizontal gridlines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((frac, i) => {
            const val = Math.round(yMax * frac);
            const y = scaleY(val);
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#1e293b"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="10"
                  fill="#64748b"
                  fontFamily="monospace"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* 95th Percentile Historical Threshold Line */}
          <line
            x1={padding.left}
            y1={thresholdY}
            x2={width - padding.right}
            y2={thresholdY}
            stroke="#f43f5e"
            strokeWidth="1.5"
            strokeDasharray="4 3"
            opacity="0.85"
          />
          <text
            x={width - padding.right + 4}
            y={thresholdY + 3}
            fontSize="9"
            fill="#f43f5e"
            fontWeight="600"
          >
            Q95 ({Math.round(thresholdVal)})
          </text>

          {/* Operational Cutoff Line (2-Week Delay Buffer) */}
          <line
            x1={originX}
            y1={padding.top}
            x2={originX}
            y2={height - padding.bottom}
            stroke="#94a3b8"
            strokeWidth="1"
            strokeDasharray="2 2"
          />
          <text
            x={originX}
            y={padding.top - 6}
            textAnchor="middle"
            fontSize="8.5"
            fill="#94a3b8"
            fontWeight="bold"
          >
            Forecast Origin (t)
          </text>

          {/* 95% Confidence Interval Band */}
          <path d={band95Path} fill="#0284c7" opacity="0.18" />

          {/* 50% Confidence Interval Band (IQR) */}
          <path d={band50Path} fill="#0284c7" opacity="0.38" />

          {/* Historical line & dots */}
          {histCoords.length > 0 && (
            <>
              <path
                d={histLinePath}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="2"
                strokeLinecap="round"
              />
              {histCoords.map((c, i) => (
                <circle key={i} cx={c.x} cy={c.y} r="3" fill="#cbd5e1" stroke="#475569" />
              ))}
            </>
          )}

          {/* Median Trajectory Line */}
          <path
            d={medianLinePath}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Forecast Points with Markers and Value Tooltip labels */}
          {forecastCoords.map((c, i) => {
            const isAnomaly = c.data.early_anomaly;
            return (
              <g key={i}>
                {/* Vertical tick */}
                <line
                  x1={c.x}
                  y1={height - padding.bottom}
                  x2={c.x}
                  y2={height - padding.bottom + 4}
                  stroke="#64748b"
                />
                {/* X Axis Label */}
                <text
                  x={c.x}
                  y={height - padding.bottom + 16}
                  textAnchor="middle"
                  fontSize="9.5"
                  fill="#94a3b8"
                  fontWeight="500"
                >
                  {c.label}
                </text>

                {/* Point dot on median */}
                <circle
                  cx={c.x}
                  cy={c.yMedian}
                  r={isAnomaly ? '5' : '4'}
                  fill={isAnomaly ? '#fbbf24' : '#0284c7'}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />

                {/* Value text above point */}
                <text
                  x={c.x}
                  y={c.yMedian - 8}
                  textAnchor="middle"
                  fontSize="9.5"
                  fontWeight="bold"
                  fill="#ffffff"
                  className="font-mono"
                >
                  {Math.round(c.data.pred_median)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* 4-Week Horizon Details Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-800">
        {forecasts.map((f) => (
          <div
            key={f.horizon}
            className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-2.5 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-300">Week +{f.horizon}</span>
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                  f.risk_tier === 'Extreme'
                    ? 'bg-rose-500/20 text-rose-400'
                    : f.risk_tier === 'High'
                    ? 'bg-orange-500/20 text-orange-400'
                    : f.risk_tier === 'Moderate'
                    ? 'bg-amber-500/20 text-amber-400'
                    : f.risk_tier === 'Insufficient Data'
                    ? 'bg-slate-700 text-slate-300'
                    : 'bg-sky-500/20 text-sky-400'
                }`}
              >
                {f.risk_tier}
              </span>
            </div>

            <div className="my-1.5">
              <div className="text-lg font-black font-mono text-white">
                {Math.round(f.pred_median)} <span className="text-xs font-normal text-slate-400">cases</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                50% IQR: [{Math.round(f.q25)} - {Math.round(f.q75)}]
              </div>
            </div>

            <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800/60">
              <span>P(Exceed Q95):</span>
              <span className="font-bold text-amber-300 font-mono">{(f.exceed_prob * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
