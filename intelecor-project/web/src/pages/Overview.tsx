import { useEffect, useState } from "react";
import { getOverview, type OverviewResponse } from "../lib/api";

// ── Severity colour maps ────────────────────────────────────────────────────
const borderColour: Record<string, string> = {
  red:    "#dc2626",
  amber:  "#6366f1",
  yellow: "#f59e0b",
  green:  "#10b981",
};
const iconColour: Record<string, string> = {
  red:    "#dc2626",
  amber:  "#6366f1",
  yellow: "#d97706",
  green:  "#10b981",
};
const actionIcon: Record<string, string> = {
  rejected_claim:  "report",
  unpaid_gap:      "warning",
  unsigned_letters:"edit_note",
  default:         "info",
};

// ── Small stat card ─────────────────────────────────────────────────────────
function StatCard({
  icon, label, value, badge, badgeColour, iconColour: iColour, sub,
}: {
  icon: string;
  label: string;
  value: string;
  badge?: string;
  badgeColour?: string;
  iconColour: string;
  sub?: string;
}) {
  return (
    <div className="neomorph-raised p-6 rounded-2xl" style={{ backgroundColor: "#e8eaf0" }}>
      <div className="flex justify-between items-start mb-4">
        <div className="p-3 neomorph-inset rounded-xl" style={{ color: iColour }}>
          <span className="material-symbols-outlined text-[22px]">{icon}</span>
        </div>
        {badge && (
          <span
            className="text-xs font-bold px-2 py-1 rounded-full"
            style={{ color: badgeColour ?? "#10b981", backgroundColor: `${badgeColour ?? "#10b981"}1a` }}
          >
            {badge}
          </span>
        )}
      </div>
      <p className="text-sm font-medium" style={{ color: "#585a68" }}>{label}</p>
      <h3 className="text-2xl font-bold mt-1" style={{ color: "#2e3040" }}>{value}</h3>
      {sub && <p className="text-[10px] font-semibold uppercase tracking-wider mt-1" style={{ color: "#585a68" }}>{sub}</p>}
    </div>
  );
}

// ── Comparison table row ─────────────────────────────────────────────────────
function CompareRow({
  label, thisWeek, lastWeek, change,
}: {
  label: string; thisWeek: string; lastWeek: string; change: string;
}) {
  const isPositive = change.startsWith("+");
  const isNeutral  = change === "—";
  return (
    <tr className="border-b" style={{ borderColor: "rgba(220,222,228,0.5)" }}>
      <td className="py-4 font-medium text-sm">{label}</td>
      <td className="py-4 text-center font-bold text-sm">{thisWeek}</td>
      <td className="py-4 text-center text-sm" style={{ color: "#585a68" }}>{lastWeek}</td>
      <td
        className="py-4 text-right font-bold text-sm"
        style={{ color: isNeutral ? "#585a68" : isPositive ? "#10b981" : "#94a3b8" }}
      >
        {change}
      </td>
    </tr>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function Overview() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="p-8">
        <div className="neomorph-raised p-6 rounded-2xl border-l-4 border-red-500 bg-red-50">
          <p className="font-semibold text-red-700">Could not load overview data</p>
          <p className="text-sm text-red-600 mt-1">{error}</p>
          <p className="text-xs text-slate-500 mt-2">Make sure the API is running at localhost:8000</p>
        </div>
      </div>
    );
  }

  const headline = data?.headline;
  const ops = (data?.operations as { summary?: { total_scheduled?: number; total_completed?: number; total_dna?: number; new_patient_count?: number; followup_count?: number; procedure_count?: number } } | null)?.summary;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">

      {/* ── Headline bento grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon="payments"
          label="Revenue This Week"
          value={headline ? `$${headline.revenue_this_week.toLocaleString()}` : "—"}
          iconColour="#6366f1"
        />
        <StatCard
          icon="group"
          label="Patients Seen"
          value={headline ? String(headline.patients_seen) : "—"}
          iconColour="#6366f1"
        />
        <StatCard
          icon="pending_actions"
          label="Outstanding Revenue"
          value={headline ? `$${headline.outstanding_revenue.toLocaleString()}` : "—"}
          iconColour="#7c3aed"
        />
        <StatCard
          icon="mail"
          label="Unsigned Letters"
          value={headline ? String(headline.unsigned_letters) : "—"}
          badge={headline && headline.unsigned_letters > 0 ? "Action required" : undefined}
          badgeColour="#dc2626"
          iconColour="#dc2626"
        />
      </div>

      {/* ── Middle row: comparison table + action items ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

        {/* Comparison table */}
        <div className="xl:col-span-2">
          <div className="neomorph-raised rounded-2xl overflow-hidden" style={{ backgroundColor: "#e8eaf0" }}>
            <div className="p-6 flex justify-between items-center">
              <h4 className="font-semibold" style={{ color: "#2e3040" }}>This week vs last week</h4>
              <button
                className="neomorph-raised px-4 py-1.5 rounded-full text-xs font-semibold hover:opacity-80 transition-all"
                style={{ color: "#6366f1" }}
              >
                Download Report
              </button>
            </div>
            <div className="px-6 pb-6 overflow-x-auto">
              <table className="w-full text-left">
                <thead
                  className="text-xs uppercase tracking-wider border-b"
                  style={{ color: "#585a68", borderColor: "#dcdee4" }}
                >
                  <tr>
                    <th className="py-3 font-semibold">Metric</th>
                    <th className="py-3 font-semibold text-center">This Week</th>
                    <th className="py-3 font-semibold text-center">Last Week</th>
                    <th className="py-3 font-semibold text-right">Change</th>
                  </tr>
                </thead>
                <tbody>
                  <CompareRow
                    label="Total appointments"
                    thisWeek={ops ? String(ops.total_scheduled) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="Completed"
                    thisWeek={ops ? String(ops.total_completed) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="New patients"
                    thisWeek={ops ? String(ops.new_patient_count) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="Follow-ups"
                    thisWeek={ops ? String(ops.followup_count) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="Procedures"
                    thisWeek={ops ? String(ops.procedure_count) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="DNAs (Did Not Attend)"
                    thisWeek={ops ? String(ops.total_dna) : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="Revenue collected"
                    thisWeek={headline ? `$${headline.revenue_this_week.toLocaleString()}` : "—"}
                    lastWeek="—"
                    change="—"
                  />
                  <CompareRow
                    label="Revenue outstanding"
                    thisWeek={headline ? `$${headline.outstanding_revenue.toLocaleString()}` : "—"}
                    lastWeek="—"
                    change="—"
                  />
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Action items */}
        <div>
          <div className="neomorph-raised p-6 rounded-2xl h-full flex flex-col" style={{ backgroundColor: "#e8eaf0" }}>
            <div className="flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined text-[20px]" style={{ color: "#6366f1" }}>task_alt</span>
              <h4 className="font-semibold" style={{ color: "#2e3040" }}>Action Items</h4>
            </div>

            <div className="space-y-4 flex-1">
              {data?.action_items && data.action_items.length > 0 ? (
                data.action_items.map((item, i) => (
                  <div
                    key={i}
                    className="neomorph-inset p-4 rounded-xl flex items-center justify-between border-l-4"
                    style={{ borderLeftColor: borderColour[item.severity] ?? "#6366f1" }}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="material-symbols-outlined text-[20px]"
                        style={{ color: iconColour[item.severity] ?? "#6366f1" }}
                      >
                        {actionIcon[item.type] ?? actionIcon.default}
                      </span>
                      <div>
                        <p className="text-sm font-semibold">{item.title}</p>
                        <p className="text-[10px]" style={{ color: "#585a68" }}>{item.subtitle}</p>
                      </div>
                    </div>
                    <span className="material-symbols-outlined text-slate-400 text-[18px]">chevron_right</span>
                  </div>
                ))
              ) : (
                /* Skeleton while loading */
                [0, 1, 2].map((i) => (
                  <div key={i} className="neomorph-inset p-4 rounded-xl h-16 animate-pulse" style={{ backgroundColor: "#dcdee4" }} />
                ))
              )}

              {/* Pad to match design if only 1-2 items */}
              {data && data.action_items.length === 0 && (
                <p className="text-sm text-center py-4" style={{ color: "#585a68" }}>No action items</p>
              )}
            </div>

            <button
              className="w-full mt-6 neomorph-raised py-3 rounded-xl text-xs font-bold uppercase tracking-widest hover:opacity-80 transition-all active:scale-[0.98]"
              style={{ color: "#6366f1" }}
            >
              View All Tasks
            </button>
          </div>
        </div>
      </div>

      {/* ── Revenue trend chart ── */}
      <div className="neomorph-raised p-8 rounded-2xl" style={{ backgroundColor: "#e8eaf0" }}>
        <div className="flex justify-between items-end mb-8">
          <div>
            <h4 className="font-semibold" style={{ color: "#2e3040" }}>Daily Revenue Trend</h4>
            <p className="text-xs mt-0.5" style={{ color: "#585a68" }}>Current month performance</p>
          </div>
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <span className="w-6 h-0.5 inline-block" style={{ backgroundColor: "#6366f1" }} />
              <span className="text-xs font-medium" style={{ color: "#585a68" }}>Current Month</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 inline-block border-b border-dashed border-slate-400" />
              <span className="text-xs font-medium" style={{ color: "#585a68" }}>Target Average</span>
            </div>
          </div>
        </div>

        <div className="relative h-64 w-full px-4">
          <svg className="w-full h-full" viewBox="0 0 1000 200" preserveAspectRatio="none">
            <line x1="0" y1="100" x2="1000" y2="100" stroke="#94a3b8" strokeDasharray="8 4" strokeWidth="1.5" />
            <path
              d="M0,150 L50,140 L100,160 L150,110 L200,120 L250,90 L300,105 L350,70 L400,85 L450,40 L500,60 L550,55 L600,75 L650,30 L700,50 L750,45 L800,65 L850,20 L900,40 L950,35 L1000,55"
              fill="none"
              stroke="#6366f1"
              strokeWidth="3"
            />
            <circle cx="500" cy="60" r="4" fill="#6366f1" />
            <circle cx="1000" cy="55" r="4" fill="#6366f1" />
          </svg>
          <div className="flex justify-between mt-2 px-1">
            {["01","05","10","15","20","25","30"].map((d) => (
              <span key={d} className="text-[10px] font-bold" style={{ color: "#585a68" }}>{d}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
