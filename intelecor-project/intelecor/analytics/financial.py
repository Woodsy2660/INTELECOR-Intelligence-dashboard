from datetime import date, timedelta
from models.billing import BillingEvent, FinancialSummary, LeakageFlag
from models.appointment import Appointment


class FinancialAnalytics:
    """
    Financial analytics module.

    Processes billing events and appointments to produce:
    - Revenue totals and collection rates
    - Revenue breakdown by billing type and MBS item
    - Revenue leakage flags (rejected claims, unbilled appointments, overdue gaps)
    - Period-over-period comparison
    """

    def analyse(
        self,
        billing_events: list[BillingEvent],
        appointments: list[Appointment],
        previous_billing: list[BillingEvent] | None = None,
    ) -> FinancialSummary:

        total_billed = sum(e.charged_amount for e in billing_events)
        total_received = sum(e.total_received for e in billing_events)
        total_outstanding = sum(e.outstanding for e in billing_events)
        collection_rate = (total_received / total_billed * 100) if total_billed > 0 else 0.0

        by_billing_type = self._group_by_billing_type(billing_events)
        by_mbs_item = self._group_by_mbs_item(billing_events)
        leakage_flags = self._detect_leakage(billing_events, appointments)

        comparison = None
        if previous_billing:
            prev_billed = sum(e.charged_amount for e in previous_billing)
            prev_received = sum(e.total_received for e in previous_billing)
            prev_outstanding = sum(e.outstanding for e in previous_billing)
            comparison = {
                "total_billed_change": self._pct_change(prev_billed, total_billed),
                "total_received_change": self._pct_change(prev_received, total_received),
                "total_outstanding_change": self._pct_change(prev_outstanding, total_outstanding),
            }

        return FinancialSummary(
            total_billed=round(total_billed, 2),
            total_received=round(total_received, 2),
            total_outstanding=round(total_outstanding, 2),
            collection_rate=round(collection_rate, 1),
            by_billing_type=by_billing_type,
            by_mbs_item=by_mbs_item,
            leakage_flags=[f.model_dump(mode="json") for f in leakage_flags],
            period_comparison=comparison,
        )

    def _group_by_billing_type(self, events: list[BillingEvent]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for e in events:
            key = e.billing_type.value
            totals[key] = totals.get(key, 0) + e.total_received
        return {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda x: -x[1])}

    def _group_by_mbs_item(self, events: list[BillingEvent]) -> dict[str, dict]:
        items: dict[str, dict] = {}
        for e in events:
            if e.mbs_item not in items:
                items[e.mbs_item] = {
                    "description": e.item_description,
                    "count": 0,
                    "total_billed": 0.0,
                    "total_received": 0.0,
                }
            items[e.mbs_item]["count"] += 1
            items[e.mbs_item]["total_billed"] += e.charged_amount
            items[e.mbs_item]["total_received"] += e.total_received

        for v in items.values():
            v["total_billed"] = round(v["total_billed"], 2)
            v["total_received"] = round(v["total_received"], 2)

        return dict(sorted(items.items(), key=lambda x: -x[1]["total_received"]))

    def _detect_leakage(
        self,
        billing_events: list[BillingEvent],
        appointments: list[Appointment],
    ) -> list[LeakageFlag]:
        flags = []

        # Rejected claims
        for e in billing_events:
            if e.claim_status.value == "rejected":
                flags.append(LeakageFlag(
                    flag_type="rejected_claim",
                    reference_id=e.invoice_id,
                    patient_id=e.patient_id,
                    service_date=e.service_date,
                    mbs_item=e.mbs_item,
                    amount=e.charged_amount,
                    detail=f"Claim rejected — {e.notes or 'review required'}",
                    severity="red",
                ))

        # Unbilled appointments (completed appointment with no matching billing event)
        billed_appt_ids = {e.appointment_id for e in billing_events if e.appointment_id}
        for appt in appointments:
            if appt.status.value == "completed" and appt.id not in billed_appt_ids:
                flags.append(LeakageFlag(
                    flag_type="unbilled_appointment",
                    reference_id=appt.id,
                    patient_id=appt.patient_id,
                    service_date=appt.scheduled_start.date(),
                    mbs_item=None,
                    amount=None,
                    detail=f"Completed {appt.appointment_type.name} with no matching invoice",
                    severity="amber",
                ))

        # Overdue gap payments (outstanding > 0, invoice older than 14 days)
        cutoff = date.today() - timedelta(days=14)
        for e in billing_events:
            if e.outstanding > 0 and e.invoice_date < cutoff:
                days_overdue = (date.today() - e.invoice_date).days
                flags.append(LeakageFlag(
                    flag_type="overdue_gap",
                    reference_id=e.invoice_id,
                    patient_id=e.patient_id,
                    service_date=e.service_date,
                    mbs_item=e.mbs_item,
                    amount=e.outstanding,
                    detail=f"Patient gap unpaid — {days_overdue} days overdue",
                    severity="yellow",
                ))

        return sorted(flags, key=lambda f: {"red": 0, "amber": 1, "yellow": 2}[f.severity])

    def _pct_change(self, old: float, new: float) -> float:
        if old == 0:
            return 0.0
        return round((new - old) / old * 100, 1)
