import React from 'react';

export interface DistrictGeoNode {
  id: string;
  name: string;
  province: string;
  x: number;
  y: number;
  w: number;
  h: number;
  shapeType?: 'rect' | 'circle';
}

// Geographically calibrated layout representation of Sri Lanka's 26 reporting units
// within a coordinate space (x: 0..460, y: 0..640)
export const SRI_LANKA_DISTRICT_COORDS: Record<string, { x: number; y: number; r: number; province: string }> = {
  // Northern Province
  'Jaffna': { x: 165, y: 55, r: 26, province: 'Northern' },
  'Kilinochchi': { x: 195, y: 110, r: 24, province: 'Northern' },
  'Mannar': { x: 135, y: 165, r: 26, province: 'Northern' },
  'Mullaitivu': { x: 255, y: 135, r: 26, province: 'Northern' },
  'Vavuniya': { x: 200, y: 180, r: 24, province: 'Northern' },

  // North Central Province
  'Anuradhapura': { x: 190, y: 240, r: 38, province: 'North Central' },
  'Polonnaruwa': { x: 275, y: 275, r: 32, province: 'North Central' },

  // Eastern Province
  'Trincomalee': { x: 290, y: 200, r: 28, province: 'Eastern' },
  'Batticaloa': { x: 335, y: 310, r: 26, province: 'Eastern' },
  'Ampara': { x: 315, y: 385, r: 34, province: 'Eastern' },
  'Kalmunai': { x: 365, y: 360, r: 22, province: 'Eastern' }, // Coastal RDHS zone

  // North Western Province
  'Puttalam': { x: 115, y: 255, r: 32, province: 'North Western' },
  'Kurunegala': { x: 165, y: 330, r: 36, province: 'North Western' },

  // Central Province
  'Matale': { x: 235, y: 320, r: 26, province: 'Central' },
  'Kandy': { x: 225, y: 375, r: 30, province: 'Central' },
  'Nuwara Eliya': { x: 240, y: 435, r: 28, province: 'Central' },

  // Sabaragamuwa Province
  'Kegalle': { x: 170, y: 395, r: 24, province: 'Sabaragamuwa' },
  'Ratnapura': { x: 205, y: 470, r: 34, province: 'Sabaragamuwa' },

  // Western Province
  'Gampaha': { x: 125, y: 370, r: 24, province: 'Western' },
  'Colombo': { x: 115, y: 420, r: 22, province: 'Western' },
  'Kalutara': { x: 130, y: 470, r: 24, province: 'Western' },

  // Uva Province
  'Badulla': { x: 285, y: 430, r: 30, province: 'Uva' },
  'Monaragala': { x: 305, y: 495, r: 34, province: 'Uva' },

  // Southern Province
  'Galle': { x: 145, y: 535, r: 26, province: 'Southern' },
  'Matara': { x: 195, y: 560, r: 26, province: 'Southern' },
  'Hambantota': { x: 270, y: 555, r: 32, province: 'Southern' },
};

interface ChoroplethMapProps {
  districtTiers: Record<string, { tier: string; cases: number; incidence: number; exceedProb: number; isAnomaly?: boolean }>;
  selectedDistrict: string;
  onSelectDistrict: (districtName: string) => void;
  selectedHorizon: number;
}

export const ChoroplethMap: React.FC<ChoroplethMapProps> = ({
  districtTiers,
  selectedDistrict,
  onSelectDistrict,
  selectedHorizon,
}) => {
  const getTierFill = (tier: string) => {
    switch (tier) {
      case 'Extreme':
        return '#dc2626'; // Deep crimson
      case 'High':
        return '#ea580c'; // Vibrant orange
      case 'Moderate':
        return '#f59e0b'; // Amber yellow
      case 'Low':
        return '#0284c7'; // Sky blue
      case 'Insufficient Data':
        return 'url(#hatched-insufficient)';
      default:
        return '#475569';
    }
  };

  const getTierBorder = (tier: string) => {
    switch (tier) {
      case 'Extreme':
        return '#f87171';
      case 'High':
        return '#fb923c';
      case 'Moderate':
        return '#fcd34d';
      case 'Low':
        return '#38bdf8';
      case 'Insufficient Data':
        return '#94a3b8';
      default:
        return '#64748b';
    }
  };

  return (
    <div className="relative w-full h-[580px] bg-slate-900/80 rounded-2xl border border-slate-800 p-4 flex flex-col shadow-inner overflow-hidden">
      {/* Map Header with Legend */}
      <div className="flex items-center justify-between mb-2 z-10">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
            <span>Sri Lanka 26 Units Risk Map</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-sky-400 font-mono">
              Horizon +{selectedHorizon}W
            </span>
          </h3>
          <p className="text-xs text-slate-400">Click a district to inspect details & fan chart</p>
        </div>

        {/* Mini Legend */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
            <span className="text-slate-300">Ext</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
            <span className="text-slate-300">High</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span className="text-slate-300">Mod</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
            <span className="text-slate-300">Low</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded bg-slate-600 border border-dashed border-slate-400"></span>
            <span className="text-slate-300">No Data</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative flex-1 flex items-center justify-center">
        <svg
          viewBox="0 0 440 620"
          className="w-full h-full max-h-[500px] drop-shadow-2xl select-none"
        >
          <defs>
            {/* SVG Hatched pattern for Insufficient Data */}
            <pattern
              id="hatched-insufficient"
              width="8"
              height="8"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="8" stroke="#94a3b8" strokeWidth="2.5" />
              <rect width="8" height="8" fill="#334155" opacity="0.6" />
            </pattern>

            {/* Pulsating glow filter for early anomalies */}
            <filter id="glow-anomaly" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Island outline hint background */}
          <ellipse cx="225" cy="360" rx="140" ry="210" fill="#0f172a" opacity="0.4" />

          {/* District Contiguity / Connection Lines */}
          <g stroke="#334155" strokeWidth="1" strokeDasharray="3 3" opacity="0.5">
            {/* Jaffna - Kilinochchi */}
            <line x1="165" y1="55" x2="195" y2="110" />
            {/* Western corridor: Colombo - Gampaha - Kalutara */}
            <line x1="115" y1="420" x2="125" y2="370" />
            <line x1="115" y1="420" x2="130" y2="470" />
            {/* Eastern corridor: Batticaloa - Kalmunai - Ampara */}
            <line x1="335" y1="310" x2="365" y2="360" />
            <line x1="365" y1="360" x2="315" y2="385" />
          </g>

          {/* District Interactive Nodes */}
          {Object.entries(SRI_LANKA_DISTRICT_COORDS).map(([name, coords]) => {
            const data = districtTiers[name] || {
              tier: 'Low',
              cases: 0,
              incidence: 0,
              exceedProb: 0,
              isAnomaly: false,
            };
            const isSelected = selectedDistrict === name;
            const isKalmunai = name === 'Kalmunai';
            const fill = getTierFill(data.tier);
            const stroke = isSelected ? '#ffffff' : getTierBorder(data.tier);
            const strokeWidth = isSelected ? 3.5 : 1.5;

            return (
              <g
                key={name}
                onClick={() => onSelectDistrict(name)}
                className="cursor-pointer group transition-transform duration-200"
              >
                {/* Highlight ring for selected district */}
                {isSelected && (
                  <circle
                    cx={coords.x}
                    cy={coords.y}
                    r={coords.r + 5}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                    className="animate-spin"
                    style={{ transformOrigin: `${coords.x}px ${coords.y}px`, animationDuration: '8s' }}
                  />
                )}

                {/* Early Anomaly Pulsing Alert Marker */}
                {data.isAnomaly && (
                  <circle
                    cx={coords.x}
                    cy={coords.y}
                    r={coords.r + 3}
                    fill="none"
                    stroke="#fbbf24"
                    strokeWidth="2"
                    className="animate-ping"
                    opacity="0.8"
                  />
                )}

                {/* District Shape (circle/bubble representation matching density) */}
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r={coords.r}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  className={`transition-all duration-200 group-hover:brightness-125 ${
                    isSelected ? 'filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]' : ''
                  }`}
                />

                {/* Special outline for Kalmunai health zone */}
                {isKalmunai && (
                  <circle
                    cx={coords.x}
                    cy={coords.y}
                    r={coords.r - 3}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="1.2"
                    strokeDasharray="2 2"
                  />
                )}

                {/* District Name Label */}
                <text
                  x={coords.x}
                  y={coords.y - 2}
                  textAnchor="middle"
                  fontSize={coords.r > 28 ? 10 : 8.5}
                  fontWeight="600"
                  fill="#ffffff"
                  pointerEvents="none"
                  className="drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]"
                >
                  {name === 'Nuwara Eliya' ? 'N. Eliya' : name === 'Anuradhapura' ? 'Anuradh.' : name}
                </text>

                {/* Subtitle Value Label (Median Cases or Insufficient) */}
                <text
                  x={coords.x}
                  y={coords.y + 10}
                  textAnchor="middle"
                  fontSize="7.5"
                  fill={data.tier === 'Insufficient Data' ? '#cbd5e1' : '#ffffff'}
                  fontWeight="500"
                  pointerEvents="none"
                  opacity="0.95"
                >
                  {data.tier === 'Insufficient Data' ? 'NO DATA' : `${Math.round(data.cases)}c`}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Map Floating Info Badge for Selected District */}
        {selectedDistrict && districtTiers[selectedDistrict] && (
          <div className="absolute bottom-2 left-2 right-2 bg-slate-950/90 backdrop-blur border border-slate-700/80 rounded-xl p-2.5 flex items-center justify-between text-xs shadow-xl">
            <div className="flex items-center gap-2">
              <span
                className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                style={{
                  backgroundColor:
                    districtTiers[selectedDistrict].tier === 'Insufficient Data'
                      ? '#64748b'
                      : getTierBorder(districtTiers[selectedDistrict].tier),
                }}
              />
              <div>
                <span className="font-bold text-white text-sm">{selectedDistrict}</span>
                <span className="text-slate-400 ml-1.5 font-medium">
                  Tier: <strong className="text-white">{districtTiers[selectedDistrict].tier}</strong>
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div>
                <span className="text-slate-400 text-[10px] uppercase block">Pred. Cases</span>
                <span className="font-mono font-bold text-sky-400">
                  {Math.round(districtTiers[selectedDistrict].cases)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase block">Incidence</span>
                <span className="font-mono font-bold text-white">
                  {districtTiers[selectedDistrict].incidence.toFixed(1)}/100k
                </span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase block">P(Exceed Q95)</span>
                <span className="font-mono font-bold text-amber-400">
                  {(districtTiers[selectedDistrict].exceedProb * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
