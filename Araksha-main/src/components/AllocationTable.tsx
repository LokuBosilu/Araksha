import React, { useState } from 'react';
import { Download, Search, AlertCircle, ArrowUpDown, ChevronRight } from 'lucide-react';

export interface AllocationRow {
  allocation_rank: number;
  district_id: string;
  district_name: string;
  province: string;
  population: number;
  piped_water_pct: number;
  max_tier: string;
  max_exceed_prob: number;
  max_incidence: number;
  priority_score: number;
  h1_cases: number;
  h2_cases: number;
  h3_cases: number;
  h4_cases: number;
  h1_tier: string;
  h2_tier: string;
  h3_tier: string;
  h4_tier: string;
  early_anomaly_flag: boolean;
  insufficient_data: boolean;
}

interface AllocationTableProps {
  rows: AllocationRow[];
  selectedDistrict: string;
  onSelectDistrict: (districtName: string) => void;
  onExportCSV: () => void;
}

export const AllocationTable: React.FC<AllocationTableProps> = ({
  rows,
  selectedDistrict,
  onSelectDistrict,
  onExportCSV,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [tierFilter, setTierFilter] = useState('ALL');

  const filteredRows = rows.filter((r) => {
    const matchesSearch =
      r.district_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.province.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = tierFilter === 'ALL' || r.max_tier === tierFilter;
    return matchesSearch && matchesTier;
  });

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'Extreme':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40';
      case 'High':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/40';
      case 'Moderate':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'Low':
        return 'bg-sky-500/20 text-sky-400 border border-sky-500/40';
      case 'Insufficient Data':
        return 'bg-slate-700/80 text-slate-300 border border-dashed border-slate-500';
      default:
        return 'bg-slate-800 text-slate-300';
    }
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-4 shadow-xl flex flex-col h-full">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>Vector-Control Allocation Matrix</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
              26 Reporting Units
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Ranked by multi-horizon composite risk score to guide 2-4 week field team deployments
          </p>
        </div>

        {/* Action Button: One-Click CSV Export */}
        <button
          onClick={onExportCSV}
          className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/20 transition-all cursor-pointer whitespace-nowrap"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Matrix (CSV)</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search district or province..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Tier filter dropdown */}
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="bg-slate-950/80 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-sky-500"
        >
          <option value="ALL">All Tiers</option>
          <option value="Extreme">Extreme</option>
          <option value="High">High</option>
          <option value="Moderate">Moderate</option>
          <option value="Low">Low</option>
          <option value="Insufficient Data">Insufficient Data</option>
        </select>
      </div>

      {/* Table Container */}
      <div className="flex-1 overflow-x-auto overflow-y-auto max-h-[460px] rounded-xl border border-slate-800/80">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400 sticky top-0 z-10 border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3 font-semibold">Rank</th>
              <th className="py-2.5 px-3 font-semibold">District</th>
              <th className="py-2.5 px-3 font-semibold">Risk Tier</th>
              <th className="py-2.5 px-3 font-semibold text-right">Proj. Cases (4W)</th>
              <th className="py-2.5 px-3 font-semibold text-right">Incidence / 100k</th>
              <th className="py-2.5 px-3 font-semibold text-right">P(Exceed Q95)</th>
              <th className="py-2.5 px-3 font-semibold text-center">Anomaly</th>
              <th className="py-2.5 px-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredRows.map((r) => {
              const isSelected = selectedDistrict === r.district_name;
              return (
                <tr
                  key={r.district_id}
                  onClick={() => onSelectDistrict(r.district_name)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-sky-950/50 text-white font-medium border-l-4 border-sky-400'
                      : 'hover:bg-slate-800/40 text-slate-300'
                  }`}
                >
                  <td className="py-2 px-3 font-bold text-slate-400">
                    #{r.allocation_rank}
                  </td>
                  <td className="py-2 px-3 font-sans">
                    <div className="font-bold text-white flex items-center gap-1.5">
                      <span>{r.district_name}</span>
                      {r.district_name === 'Kalmunai' && (
                        <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                          RDHS
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-slate-500 font-sans">{r.province}</div>
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-block text-[10px] font-sans font-bold px-2 py-0.5 rounded-full ${getTierBadge(
                        r.max_tier
                      )}`}
                    >
                      {r.max_tier}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right">
                    {r.insufficient_data ? (
                      <span className="text-slate-500 italic font-sans">No Data</span>
                    ) : (
                      <span className="font-bold text-white">
                        {Math.round(r.h1_cases + r.h2_cases + r.h3_cases + r.h4_cases)}
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {r.insufficient_data ? (
                      <span className="text-slate-500">—</span>
                    ) : (
                      <span className="text-slate-200">{r.max_incidence.toFixed(1)}</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {r.insufficient_data ? (
                      <span className="text-slate-500">—</span>
                    ) : (
                      <span
                        className={`font-bold ${
                          r.max_exceed_prob >= 0.5 ? 'text-amber-400' : 'text-slate-300'
                        }`}
                      >
                        {(r.max_exceed_prob * 100).toFixed(0)}%
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {r.early_anomaly_flag ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-sans font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        <AlertCircle className="w-3 h-3 text-amber-400" />
                        <span>ALERT</span>
                      </span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-slate-500">
                    <ChevronRight className="w-3.5 h-3.5" />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
