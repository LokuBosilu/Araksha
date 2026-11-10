import React from 'react';
import { X, Info, ShieldCheck, AlertTriangle, Layers, Calendar, HelpCircle } from 'lucide-react';

interface HowToReadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HowToReadModal: React.FC<HowToReadModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative text-slate-200">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
            <Info className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">How to Read This Forecaster</h2>
            <p className="text-xs text-slate-400">Decision-support guide for district vector-control & MOH officers</p>
          </div>
        </div>

        {/* Core Explanations */}
        <div className="space-y-4 text-xs leading-relaxed">
          {/* 1. What does the 4-week horizon mean? */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Calendar className="w-4 h-4 text-sky-400" />
              <span>Why 4 Weeks Ahead? (Operational Lead Time)</span>
            </h4>
            <p className="text-slate-300">
              Vector-control interventions (larviciding, source reduction campaigns, drain clearing, and adult fogging)
              require <strong>2 to 4 weeks</strong> to reduce adult mosquito populations and suppress transmission cycles.
              A forecast at horizon <strong>+2W to +4W</strong> allows MOH teams to stage manpower and chemicals before
              clinics see an influx of fever patients.
            </p>
          </div>

          {/* 2. Exceedance Probability Explained */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>What is Exceedance Probability P(Exceed Q95)?</span>
            </h4>
            <p className="text-slate-300 mb-1.5">
              Each district has an established historical <strong>95th-percentile weekly caseload threshold (Q95)</strong>
              calculated strictly from pre-forecast surveillance data.
            </p>
            <ul className="list-disc pl-5 space-y-1 text-slate-400">
              <li><strong>P &lt; 15% (Low Concern)</strong>: Normal seasonal variation. Routine maintenance.</li>
              <li><strong>15% &le; P &lt; 50% (Moderate)</strong>: Rising vector index. Intensify inspection.</li>
              <li><strong>P &ge; 50% (High/Extreme Outbreak Alert)</strong>: Imminent epidemic conditions. Deploy fogging units and activate local health task forces.</li>
            </ul>
          </div>

          {/* 3. Prediction Intervals (50% and 95%) */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>How to Use the Fan Chart Bands</span>
            </h4>
            <p className="text-slate-300 mb-1">
              Predictive uncertainty reflects real-world variability in weather, reporting, and human behavior:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-slate-400">
              <li><strong>Solid Line (Median)</strong>: The central projection: half of realistic outcomes lie above, half below.</li>
              <li><strong>Inner Band (50% IQR)</strong>: The most likely range of cases for baseline logistics planning.</li>
              <li><strong>Outer Band (95% Interval)</strong>: The surge capacity planning range for emergency hospital bed and medication readiness.</li>
            </ul>
          </div>

          {/* 4. Insufficient Data Fail-Safe */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>The 'Insufficient Data' Safety Rule</span>
            </h4>
            <p className="text-slate-300">
              If an external hospital reporting stream or weather sensor is interrupted or delayed, the system
              <strong> never defaults to Low Risk</strong>. Instead, it explicitly marks the unit as
              <strong> 'Insufficient Data' (hatched slate pattern)</strong> to alert officers that field data is missing,
              preventing catastrophic false reassurance.
            </p>
          </div>

          {/* 5. Early Anomaly Flag */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <HelpCircle className="w-4 h-4 text-rose-400" />
              <span>Early Anomaly Alert</span>
            </h4>
            <p className="text-slate-300">
              Triggers when a district’s forecasted caseload is <strong>&ge; 2.0x higher than its seasonal norm</strong>
              even while current clinical hospital admissions appear low. This flags covert vector proliferation weeks
              before symptoms appear in the population.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs transition-colors"
          >
            Understood & Close
          </button>
        </div>
      </div>
    </div>
  );
};
