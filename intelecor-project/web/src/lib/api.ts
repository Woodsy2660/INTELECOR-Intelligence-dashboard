const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface OverviewHeadline {
  revenue_this_week: number;
  patients_seen: number;
  outstanding_revenue: number;
  unsigned_letters: number;
}

export interface ActionItem {
  type: string;
  title: string;
  subtitle: string;
  severity: "red" | "amber" | "yellow" | "green";
  link: string;
}

export interface OverviewResponse {
  headline: OverviewHeadline;
  financial: Record<string, unknown> | null;
  operations: Record<string, unknown> | null;
  documents: Record<string, unknown> | null;
  action_items: ActionItem[];
}

export interface LeakageFlag {
  flag_type: string;
  severity: "red" | "amber" | "yellow";
  reference_id: string;
  patient_id: string;
  service_date: string;
  mbs_item: string | null;
  amount: number | null;
  detail: string;
}

export interface FinancialSummary {
  total_billed: number;
  total_received: number;
  total_outstanding: number;
  collection_rate: number;
  by_billing_type: Record<string, number>;
  by_mbs_item: Record<string, { description: string; count: number; total_billed: number; total_received: number }>;
  leakage_flags: LeakageFlag[];
  period_comparison: Record<string, number> | null;
}

export interface FinancialLeakageResponse {
  flags: LeakageFlag[];
  source: string;
  fetched_at: string;
}

export interface AppointmentSummary {
  total_scheduled: number;
  total_completed: number;
  total_dna: number;
  total_cancelled: number;
  completion_rate: number;
  dna_rate: number;
  new_patient_count: number;
  followup_count: number;
  procedure_count: number;
  new_patient_ratio: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  by_day: Record<string, Record<string, number>>;
}

export interface OperationsSummary {
  summary: AppointmentSummary;
  referral_sources: { practice: string; count: number }[];
}

export interface DocumentsSummary {
  total_unsigned: number;
  total_signed_unsent: number;
  avg_days_to_sign: number;
  by_age_bracket: Record<string, number>;
  by_type: Record<string, number>;
  weekly_created: number[];
  weekly_signed: number[];
  unsigned_queue: {
    id: string;
    patient_id: string;
    letter_type: string;
    recipient_name: string;
    recipient_practice: string | null;
    created_at: string;
    days_unsigned: number;
    dictation_source: string | null;
  }[];
}

export interface DocumentsQueueResponse {
  queue: {
    id: string;
    patient_id: string;
    letter_type: string;
    recipient_name: string;
    recipient_practice: string | null;
    created_at: string;
    days_unsigned: number;
    source: string | null;
  }[];
  source: string;
  fetched_at: string;
}

// ── API calls ──────────────────────────────────────────────────────────────

export const getOverview = () => get<OverviewResponse>("/api/overview/summary");
export const getFinancialSummary = () => get<FinancialSummary>("/api/financial/summary");
export const getFinancialLeakage = () => get<FinancialLeakageResponse>("/api/financial/leakage");
export const getOperationsSummary = () => get<OperationsSummary>("/api/operations/summary");
export const getDocumentsSummary = () => get<DocumentsSummary>("/api/documents/summary");
export const getDocumentsQueue = () => get<DocumentsQueueResponse>("/api/documents/queue");
