from collections import defaultdict
from models.document import Document, DocumentSummary


class DocumentsAnalytics:
    """
    Documents analytics module.

    Processes correspondence/letter records to produce:
    - Unsigned letter counts and ageing brackets
    - Signed-but-unsent tracking
    - Average time to sign
    - Weekly creation vs signing trends (backlog tracking)
    """

    def analyse(self, documents: list[Document]) -> DocumentSummary:
        unsigned = [d for d in documents if d.status.value == "unsigned"]
        signed_unsent = [d for d in documents
                         if d.status.value == "signed" and d.sent_at is None]
        signed_or_sent = [d for d in documents
                          if d.status.value in ("signed", "sent") and d.signed_at]

        avg_days = 0.0
        if signed_or_sent:
            total_days = sum(
                (d.signed_at - d.created_at).days for d in signed_or_sent
            )
            avg_days = round(total_days / len(signed_or_sent), 1)

        by_age = self._age_brackets(unsigned)
        by_type = self._group_by_type(documents)

        weekly_created, weekly_signed = self._weekly_pipeline(documents)

        unsigned_queue = [
            {
                "id": d.id,
                "patient_id": d.patient_id,
                "letter_type": d.letter_type.value,
                "recipient_name": f"{d.recipient.given_name} {d.recipient.family_name}",
                "recipient_practice": d.recipient.practice_name,
                "created_at": d.created_at.isoformat(),
                "days_unsigned": d.days_unsigned,
                "dictation_source": d.dictation_source.value if d.dictation_source else None,
            }
            for d in sorted(unsigned, key=lambda x: -x.days_unsigned)
        ]

        return DocumentSummary(
            total_unsigned=len(unsigned),
            total_signed_unsent=len(signed_unsent),
            avg_days_to_sign=avg_days,
            by_age_bracket=by_age,
            by_type=by_type,
            weekly_created=weekly_created,
            weekly_signed=weekly_signed,
            unsigned_queue=unsigned_queue,
        )

    def _age_brackets(self, unsigned: list[Document]) -> dict[str, int]:
        brackets = {"0-2d": 0, "3-5d": 0, "6-10d": 0, "10d+": 0}
        for d in unsigned:
            days = d.days_unsigned
            if days <= 2:
                brackets["0-2d"] += 1
            elif days <= 5:
                brackets["3-5d"] += 1
            elif days <= 10:
                brackets["6-10d"] += 1
            else:
                brackets["10d+"] += 1
        return brackets

    def _group_by_type(self, documents: list[Document]) -> dict[str, int]:
        types: dict[str, int] = defaultdict(int)
        for d in documents:
            types[d.letter_type.value] += 1
        return dict(types)

    def _weekly_pipeline(
        self, documents: list[Document]
    ) -> tuple[list[int], list[int]]:
        created_by_week: dict[int, int] = defaultdict(int)
        signed_by_week: dict[int, int] = defaultdict(int)

        for d in documents:
            week = d.created_at.isocalendar()[1]
            created_by_week[week] += 1
            if d.signed_at:
                sign_week = d.signed_at.isocalendar()[1]
                signed_by_week[sign_week] += 1

        if not created_by_week:
            return [], []

        all_weeks = sorted(set(list(created_by_week.keys()) + list(signed_by_week.keys())))
        last_4 = all_weeks[-4:] if len(all_weeks) >= 4 else all_weeks

        return (
            [created_by_week.get(w, 0) for w in last_4],
            [signed_by_week.get(w, 0) for w in last_4],
        )
