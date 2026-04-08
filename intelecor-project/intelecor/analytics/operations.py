from collections import defaultdict
from models.appointment import Appointment, AppointmentSummary
from models.referral import Referral


class OperationsAnalytics:
    """
    Operations analytics module.

    Processes appointments and referrals to produce:
    - Appointment volumes, completion rates, DNA rates
    - New vs follow-up patient ratios
    - Breakdown by appointment type and daily status
    - Referral source analysis
    """

    def analyse(
        self,
        appointments: list[Appointment],
        previous_appointments: list[Appointment] | None = None,
        referrals: list[Referral] | None = None,
    ) -> dict:

        scheduled = [a for a in appointments if a.status.value != "cancelled"]
        completed = [a for a in appointments if a.status.value == "completed"]
        dna = [a for a in appointments if a.did_not_arrive]
        cancelled = [a for a in appointments if a.status.value == "cancelled"]
        new_patients = [a for a in completed if a.is_new_patient]
        followups = [a for a in completed if not a.is_new_patient
                     and a.appointment_type.category.value == "consultation"]
        procedures = [a for a in completed
                      if a.appointment_type.category.value == "procedure"]

        total_scheduled = len(scheduled)
        completion_rate = (len(completed) / total_scheduled * 100) if total_scheduled > 0 else 0.0
        dna_rate = (len(dna) / total_scheduled * 100) if total_scheduled > 0 else 0.0
        new_ratio = (len(new_patients) / len(completed) * 100) if completed else 0.0

        by_type = defaultdict(int)
        for a in completed:
            by_type[a.appointment_type.name] += 1

        by_status = {
            "completed": len(completed),
            "did_not_arrive": len(dna),
            "cancelled": len(cancelled),
            "booked": len([a for a in appointments if a.status.value in ("booked", "confirmed")]),
        }

        by_day = self._group_by_day(appointments)

        result = {
            "summary": AppointmentSummary(
                total_scheduled=total_scheduled,
                total_completed=len(completed),
                total_dna=len(dna),
                total_cancelled=len(cancelled),
                completion_rate=round(completion_rate, 1),
                dna_rate=round(dna_rate, 1),
                new_patient_count=len(new_patients),
                followup_count=len(followups),
                procedure_count=len(procedures),
                new_patient_ratio=round(new_ratio, 1),
                by_type=dict(by_type),
                by_status=by_status,
                by_day=by_day,
            ).model_dump(),
            "referral_sources": self._referral_sources(referrals) if referrals else [],
        }

        if previous_appointments:
            result["comparison"] = self._compare(appointments, previous_appointments)

        return result

    def _group_by_day(self, appointments: list[Appointment]) -> dict[str, dict[str, int]]:
        days: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for a in appointments:
            day = a.scheduled_start.strftime("%A")
            if a.status.value == "completed":
                days[day]["completed"] += 1
            elif a.did_not_arrive:
                days[day]["dna"] += 1
            elif a.status.value == "cancelled":
                days[day]["cancelled"] += 1
            else:
                days[day]["booked"] += 1
        return {k: dict(v) for k, v in days.items()}

    def _referral_sources(self, referrals: list[Referral]) -> list[dict]:
        sources: dict[str, int] = defaultdict(int)
        for r in referrals:
            sources[r.referring_doctor.practice_name] += 1
        return [
            {"practice": k, "count": v}
            for k, v in sorted(sources.items(), key=lambda x: -x[1])
        ]

    def _compare(
        self,
        current: list[Appointment],
        previous: list[Appointment],
    ) -> dict:
        cur_completed = len([a for a in current if a.status.value == "completed"])
        prev_completed = len([a for a in previous if a.status.value == "completed"])
        cur_dna = len([a for a in current if a.did_not_arrive])
        prev_dna = len([a for a in previous if a.did_not_arrive])
        cur_new = len([a for a in current if a.is_new_patient and a.status.value == "completed"])
        prev_new = len([a for a in previous if a.is_new_patient and a.status.value == "completed"])

        return {
            "completed": {"current": cur_completed, "previous": prev_completed,
                          "change": self._pct(prev_completed, cur_completed)},
            "dna": {"current": cur_dna, "previous": prev_dna,
                    "change": self._pct(prev_dna, cur_dna)},
            "new_patients": {"current": cur_new, "previous": prev_new,
                             "change": self._pct(prev_new, cur_new)},
        }

    def _pct(self, old: int, new: int) -> float:
        if old == 0:
            return 0.0
        return round((new - old) / old * 100, 1)
