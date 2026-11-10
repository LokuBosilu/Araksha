import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Info,
  Calendar,
  Layers,
  Activity,
  FileText,
  MapPin,
  RefreshCw,
  HelpCircle,
  TrendingUp,
  Download,
  Flame,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';

import forecastData from './data/forecast_data.json';
import { ChoroplethMap } from './components/ChoroplethMap';
import { FanChart, ForecastPoint } from './components/FanChart';
import { AllocationTable, AllocationRow } from './components/AllocationTable';
import { HowToReadModal } from './components/HowToReadModal';
import { DocumentationView } from './components/DocumentationView';

export default function App() {
  const [selectedHorizon, setSelectedHorizon] = useState<number>(1);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('Colombo');
  const [activeScenarioKey, setActiveScenarioKey] = useState<string>('latest_2024');
  const [showHowToRead, setShowHowToRead] = useState<boolean>(false);
  const [activeView, setActiveView] = useState<'dashboard' | 'documentation'>('dashboard');

  // Load current active scenario
  const currentScenario = useMemo(() => {
    return (forecastData.scenarios as any)[activeScenarioKey] || (forecastData.scenarios as any)['latest_2024'];
  }, [activeScenarioKey]);

  const metadata = currentScenario.metadata;
  const forecastsList = currentScenario.forecasts as ForecastPoint[];
  const allocationList = currentScenario.allocation as AllocationRow[];

  // District tiers dictionary for selected horizon
  const districtTiers = useMemo(() => {
    const map: Record<string, { tier: string; cases: number; incidence: number; exceedProb: number; isAnomaly?: boolean }> = {};
    forecastsList
      .filter((f) => f.horizon === selectedHorizon)
      .forEach((f) => {
        map[(f as any).district_name] = {
          tier: f.risk_tier,
          cases: f.pred_median,
          incidence: f.incidence_per_100k,
          exceedProb: f.exceed_prob,
          isAnomaly: f.early_anomaly,
        };
      });
    return map;
  }, [forecastsList, selectedHorizon]);

  // Selected district 4-week forecast trajectory
  const selectedDistrictForecasts = useMemo(() => {
    return forecastsList
      .filter((f: any) => f.district_name === selectedDistrict)
      .sort((a, b) => a.horizon - b.horizon);
  }, [forecastsList, selectedDistrict]);

  // Selected district recent historical cases
  const selectedDistrictHistory = useMemo(() => {
    const raw = (forecastData.history_by_district as any)[selectedDistrict] || [];
    // Last 6 weeks for historical context
    return raw.slice(-6).map((r: any) => ({
      week: r.week,
      cases: r.cases,
    }));
  }, [selectedDistrict]);

  // Handle CSV export of the Allocation Matrix
  const handleExportCSV = () => {
    const headers = [
      'allocation_rank',
      'district_name',
      'province',
      'population',
      'max_tier',
      'max_incidence',
      'max_exceed_prob',
      'priority_score',
      'h1_cases',
      'h2_cases',
      'h3_cases',
      'h4_cases',
      'early_anomaly_flag',
      'insufficient_data',
    ];
    const csvRows = [
      headers.join(','),
      ...allocationList.map((r) =>
        [
          r.allocation_rank,
          `"${r.district_name}"`,
          `"${r.province}"`,
          r.population,
          `"${r.max_tier}"`,
          r.max_incidence,
          r.max_exceed_prob,
          r.priority_score,
          r.h1_cases,
          r.h2_cases,
          r.h3_cases,
          r.h4_cases,
          r.early_anomaly_flag,
          r.insufficient_data,
        ].join(',')
      ),
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `silentnode_allocation_matrix_${metadata.as_of_origin}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Tier summary metrics for active horizon
  const horizonTierCounts = useMemo(() => {
    const counts = { Extreme: 0, High: 0, Moderate: 0, Low: 0, 'Insufficient Data': 0 };
    Object.values(districtTiers).forEach((d) => {
      if ((counts as any)[d.tier] !== undefined) {
        (counts as any)[d.tier]++;
      }
    });
    return counts;
  }, [districtTiers]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-sky-500 selection:text-white">
      {/* 1. Permanent Non-Clinical Disclaimer Banner */}
      <div className="bg-gradient-to-r from-amber-950 via-slate-900 to-amber-950 border-b border-amber-800/40 px-4 py-2 text-center text-xs text-amber-300 flex items-center justify-center gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
        <span>
          <strong>Operational Planning Notice</strong>: Silent Node is a planning decision-support tool for district
          vector-control & Medical Officers of Health (MOH), <strong>NOT a clinical diagnostic tool</strong>.
        </span>
      </div>

      {/* 2. Top Header & Freshness Information Bar */}
      <header className="bg-slate-900/90 border-b border-slate-800 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Brand & System Identity */}
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 shadow-lg shadow-sky-500/20 text-white">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-wider text-white">ARAKSHA</h1>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-sky-400 font-mono font-bold">
                  v1.0.0
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                  26 Reporting Units
                </span>
              </div>
              <p className="text-xs text-slate-400">
                4-Week District Dengue Risk Forecaster & Resource Allocation Engine
              </p>
            </div>
          </div>

          {/* Freshness & Metadata Badges */}
          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5 flex items-center gap-2">
              <Calendar className="w-3.5 h-3.5 text-sky-400" />
              <div>
                <span className="text-slate-500 text-[10px] uppercase block leading-none">Forecast Origin</span>
                <span className="font-mono font-bold text-white">{metadata.as_of_origin}</span>
              </div>
            </div>

            <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5 flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <div>
                <span className="text-slate-500 text-[10px] uppercase block leading-none">Data Cutoff</span>
                <span className="font-mono font-bold text-emerald-400">{metadata.data_cutoff_week}</span>
              </div>
            </div>

            {/* View Switcher: Dashboard vs Documentation */}
            <div className="flex items-center bg-slate-950 border border-slate-800 rounded-xl p-1">
              <button
                onClick={() => setActiveView('dashboard')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  activeView === 'dashboard'
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveView('documentation')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  activeView === 'documentation'
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Docs & Evaluation
              </button>
            </div>

            {/* Help Button */}
            <button
              onClick={() => setShowHowToRead(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
              <span>How to Read This</span>
            </button>
          </div>
        </div>

        {/* Scenario Switcher Bar */}
        <div className="bg-slate-950/90 border-t border-slate-800/80 px-4 py-2">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-semibold uppercase text-[11px] tracking-wider flex items-center gap-1">
                <RefreshCw className="w-3 h-3 text-sky-400" />
                <span>Simulation / Origin Scenario:</span>
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {Object.entries(forecastData.scenarios).map(([key, sc]: [string, any]) => (
                  <button
                    key={key}
                    onClick={() => setActiveScenarioKey(key)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                      activeScenarioKey === key
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-400/50 shadow-sm'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    {key === 'latest_2024'
                      ? 'Live Operational (2024-W20)'
                      : key === 'replay_2017_outbreak'
                      ? 'Replay: May 1, 2017 (--as-of 2017-05-01)'
                      : 'Data Interruption Test (Kalmunai)'}
                  </button>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 italic">
              {currentScenario.description}
            </p>
          </div>
        </div>
      </header>

      {/* Prominent Staleness Banner when Flagged */}
      {metadata.staleness_flag && (
        <div className="bg-rose-950/90 border-b border-rose-800 px-4 py-3 animate-pulse">
          <div className="max-w-7xl mx-auto flex items-center gap-3 text-rose-200 text-xs">
            <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <div>
              <strong className="text-white font-bold block text-sm">
                DATA STALENESS & SURVEILLANCE INTERRUPTION DETECTED
              </strong>
              <span>
                One or more reporting inputs (e.g., Kalmunai health zone) were missing or delayed beyond threshold.
                Predictive variance has been expanded by 1.5x. Missing districts produce{' '}
                <strong>'Insufficient Data'</strong> and <strong>never default to Low Risk</strong>.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Body Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {activeView === 'documentation' ? (
          <DocumentationView />
        ) : (
          <>
            {/* Horizon Selector and Summary Metric Cards */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Horizon Tabs (1 to 4 weeks ahead) */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-sky-400" />
                  <span>Horizon:</span>
                </span>
                {[1, 2, 3, 4].map((h) => {
                  const targetSample = forecastsList.find((f) => f.horizon === h);
                  const isSelected = selectedHorizon === h;
                  return (
                    <button
                      key={h}
                      onClick={() => setSelectedHorizon(h)}
                      className={`flex flex-col items-center px-4 py-2 rounded-xl border text-xs font-semibold transition-all ${
                        isSelected
                          ? 'bg-sky-600 border-sky-400 text-white shadow-lg shadow-sky-600/30'
                          : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
                      }`}
                    >
                      <span className="text-sm font-bold">Week +{h}</span>
                      <span className={`text-[10px] font-mono ${isSelected ? 'text-sky-200' : 'text-slate-500'}`}>
                        Target: W{targetSample ? targetSample.target_week : ''}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* District Tier Counts for Horizon */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <div className="flex items-center gap-2 bg-slate-950 border border-rose-900/60 rounded-xl px-3 py-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
                  <span className="text-slate-400">Extreme:</span>
                  <span className="font-mono font-bold text-rose-400">{horizonTierCounts.Extreme}</span>
                </div>

                <div className="flex items-center gap-2 bg-slate-950 border border-orange-900/60 rounded-xl px-3 py-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
                  <span className="text-slate-400">High:</span>
                  <span className="font-mono font-bold text-orange-400">{horizonTierCounts.High}</span>
                </div>

                <div className="flex items-center gap-2 bg-slate-950 border border-amber-900/60 rounded-xl px-3 py-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                  <span className="text-slate-400">Moderate:</span>
                  <span className="font-mono font-bold text-amber-400">{horizonTierCounts.Moderate}</span>
                </div>

                <div className="flex items-center gap-2 bg-slate-950 border border-sky-900/60 rounded-xl px-3 py-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
                  <span className="text-slate-400">Low:</span>
                  <span className="font-mono font-bold text-sky-400">{horizonTierCounts.Low}</span>
                </div>

                {horizonTierCounts['Insufficient Data'] > 0 && (
                  <div className="flex items-center gap-2 bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5">
                    <span className="w-2.5 h-2.5 rounded bg-slate-500 border border-dashed border-slate-300"></span>
                    <span className="text-slate-400">No Data:</span>
                    <span className="font-mono font-bold text-slate-300">
                      {horizonTierCounts['Insufficient Data']}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Top Grid: Left Choropleth Map (1/2) and Right Allocation Matrix (1/2) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Interactive Choropleth Map */}
              <div className="lg:col-span-5">
                <ChoroplethMap
                  districtTiers={districtTiers}
                  selectedDistrict={selectedDistrict}
                  onSelectDistrict={setSelectedDistrict}
                  selectedHorizon={selectedHorizon}
                />
              </div>

              {/* Right Column: Ranked Vector-Control Allocation Matrix */}
              <div className="lg:col-span-7">
                <AllocationTable
                  rows={allocationList}
                  selectedDistrict={selectedDistrict}
                  onSelectDistrict={setSelectedDistrict}
                  onExportCSV={handleExportCSV}
                />
              </div>
            </div>

            {/* Bottom Row: Selected District Detail & 4-Week Fan Chart */}
            <div className="space-y-4">
              <FanChart
                districtName={selectedDistrict}
                forecasts={selectedDistrictForecasts}
                recentHistory={selectedDistrictHistory}
                cutoffWeekStr={metadata.data_cutoff_week}
              />

              {/* District Demographic & Environmental Covariates Context Strip */}
              {selectedDistrictForecasts[0] && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl">
                  <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Province & Jurisdiction</span>
                      <span className="font-bold text-white text-sm">
                        {selectedDistrictForecasts[0].province} Province
                        {selectedDistrict === 'Kalmunai' && ' (RDHS Health Zone)'}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Estimated 2023 Population</span>
                      <span className="font-mono font-bold text-white text-sm">
                        {((selectedDistrictForecasts[0] as any).population || 500000).toLocaleString()}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Piped-Water Access Share</span>
                      <span className="font-mono font-bold text-sky-400 text-sm">
                        {(selectedDistrictForecasts[0] as any).piped_water_pct || 35.0}%
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Historical Q95 Baseline</span>
                      <span className="font-mono font-bold text-rose-400 text-sm">
                        {selectedDistrictForecasts[0].threshold_q95} cases/week
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Model Formulation</span>
                      <span className="font-semibold text-slate-300 text-sm">
                        Ensemble (GAM + Seasonal-AR)
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-800/80 py-4 px-4 mt-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-400">Silent Node Dengue Forecaster</span>
            <span>•</span>
            <span>Sri Lanka 26 Reporting Units</span>
            <span>•</span>
            <span>Direct Multi-Horizon Leakage-Safe Architecture</span>
          </div>
          <div>
            <span>Data: denguedatahub (Talagala) • Open-Meteo ERA5 • CPH-2024 • OCHA COD-PS</span>
          </div>
        </div>
      </footer>

      {/* Explainer Modal */}
      <HowToReadModal isOpen={showHowToRead} onClose={() => setShowHowToRead(false)} />
    </div>
  );
}
