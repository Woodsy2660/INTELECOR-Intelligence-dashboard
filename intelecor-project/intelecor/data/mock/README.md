# INTELECOR Mock Data — Gentu Simulation
## Reference for Adapter Layer Development

---

## Files Overview

| File | Simulates | Format | Records |
|------|-----------|--------|---------|
| `healthcare_api_appointments.json` | Healthcare API — GET /tenants/{id}/appointments | JSON | 8 appointments |
| `letters_api_correspondence.json` | Letters API — outgoing correspondence pipeline | JSON | 10 letters |
| `bookings_api_practitioners.json` | Bookings API — practitioners, locations, referrals | JSON | 1 practitioner, 2 locations, 4 referrals |
| `gentu_billing_export.csv` | Gentu CSV export — billing/financial (no API available) | CSV | 20 invoice lines |

---

## Healthcare API — Appointments

### What the adapter receives
Paginated JSON response with appointment records including nested patient, practitioner, location, appointment_type, and referral objects.

### Key fields your adapter must extract

**Appointment level:**
- `id` — unique appointment identifier (string)
- `status` — enum: `booked`, `confirmed`, `arrived`, `in_consult`, `completed`, `did_not_arrive`, `cancelled`
- `scheduled_start` / `scheduled_end` — ISO 8601 with timezone
- `actual_start` / `actual_end` — null if not yet occurred or DNA
- `did_not_arrive` — boolean flag for DNA tracking
- `is_new_patient` — boolean, drives new vs follow-up reporting
- `cancellation_reason` — free text, null if not cancelled

**Nested patient object:**
- `id`, `given_name`, `family_name`, `date_of_birth`, `gender`
- `medicare_number` (10 digits), `medicare_irn` (1-9), `dva_file_number`
- `concession_type` — null, `pension`, `healthcare_card`, `dva_gold`, `dva_white`
- Privacy note: patient-level data stays local. Only aggregate counts reach the LLM.

**Nested appointment_type object:**
- `id`, `name`, `duration_minutes`, `category` (consultation / procedure)
- This is the primary grouping key for operational analytics

**Nested referral object:**
- `referring_doctor` with `provider_number` and `practice_name`
- `referral_date`, `valid_to` — critical for expiry tracking
- `referral_reason` — free text from GP

### What the adapter outputs to the normalisation layer
Flat internal `Appointment` model with denormalised patient_id, practitioner_id, appointment_type_category, referral_id. Nested objects broken into separate internal models (Patient, Referral).

---

## Letters API — Correspondence

### What the adapter receives
JSON response with letter records following Gentu's outgoing correspondence workflow.

### Key fields your adapter must extract

- `id` — unique letter identifier
- `patient_id`, `practitioner_id`, `appointment_id` — links back to source
- `letter_type` — enum: `consultation_report`, `procedure_report`, `referral_letter`, `discharge_summary`
- `status` — enum following the pipeline: `draft` → `unsigned` → `signed` → `sent`
- `dictation_source` — `heidi_ai_scribe`, `manual_dictation`, `voicebox`, `typed`
- `days_unsigned` — integer, calculated field for ageing analysis
- `signed_at`, `sent_at` — timestamps, null until actioned
- `sent_method` — `medical_objects`, `email`, `fax`, `post`, null if not sent
- `recipient` — referring doctor details for the letter

### Analytics this drives
- **Document tracking module:** counts of unsigned letters by age bracket (1-3 days, 4-7 days, 8-14 days, 14+ days)
- **Operational efficiency:** average time from appointment to letter signed, average time from signed to sent
- **Bottleneck detection:** letters unsigned for 7+ days flagged as action items

---

## Bookings API — Practitioners, Locations, Referrals

### What the adapter receives
JSON response with practitioner profiles, location details, schedule/availability, and referral records.

### Key fields — Practitioners
- `id`, `given_name`, `family_name`
- `provider_numbers` — array, one per location (critical for billing)
- `specialty`, `ahpra_number`
- `appointment_types` — defines what services this practitioner offers
- `schedule.weekly_availability` — day, location, start/end times, break times
- `schedule.blocked_dates` — holidays, conferences, leave

### Key fields — Referrals
- `id`, `patient_id`
- `referring_doctor` — full details including provider number
- `referral_date`, `valid_to`, `referral_period_months`
- `urgency` — `routine`, `semi_urgent`, `urgent`
- `status` — `active`, `pending_appointment`, `expired`, `completed`
- `linked_appointment_id` — null if referral received but not yet booked

### Analytics this drives
- **Referral pipeline:** referrals received vs booked vs pending
- **Referral source analysis:** which GPs send the most referrals
- **Expiry alerts:** referrals approaching expiry without a booked appointment
- **Wait time:** days from referral received to first appointment

---

## Billing CSV Export — Financial Data

### Why this is CSV not JSON
Gentu's billing/financial endpoints are not exposed through the developer partner API. Financial data must come via Gentu's built-in CSV/Excel export functionality. The adapter for this data source parses CSV rather than calling a REST endpoint.

### Column definitions

| Column | Type | Description |
|--------|------|-------------|
| Invoice ID | string | Unique invoice identifier, format INV-YYYYMMDD-NNN |
| Invoice Date | date | Date invoice was created |
| Patient ID | string | Links to patient in Healthcare API |
| Patient Name | string | Full name (for display in Gentu, stripped by adapter) |
| DOB | date | Patient date of birth |
| Practitioner | string | Billing practitioner name |
| Provider Number | string | Medicare provider number used for this claim |
| Location | string | Practice location name |
| Appointment ID | string | Links to appointment in Healthcare API |
| Service Date | date | Date service was provided |
| MBS Item | string | Medicare Benefits Schedule item number |
| Item Description | string | MBS item description |
| Schedule Fee | decimal | MBS schedule fee for this item |
| Charged Amount | decimal | Amount the practice actually charged |
| Billing Type | enum | `private`, `bulk_bill`, `dva`, `eclipse_no_gap`, `eclipse_known_gap`, `eclipse_patient_claim`, `workcover` |
| Claim Status | enum | `draft`, `submitted`, `accepted`, `rejected`, `pending` |
| Payment Status | enum | `unpaid`, `partial`, `paid` |
| Medicare Benefit | decimal | Amount paid by Medicare (85% of schedule fee for private, 100% for bulk bill) |
| Gap Amount | decimal | Difference between charged amount and Medicare benefit |
| Patient Paid | decimal | Amount received from patient |
| Insurer Paid | decimal | Amount received from private health insurer (ECLIPSE) |
| DVA Amount | decimal | Amount received from DVA |
| Total Received | decimal | Sum of all payments received |
| Outstanding | decimal | Charged Amount minus Total Received |
| Claim Submitted Date | date | When Medicare/DVA claim was submitted |
| Claim Processed Date | date | When claim was processed by Medicare/DVA |
| Payment Received Date | date | When payment was received (null if outstanding) |
| Referring Doctor | string | Referring doctor name |
| Referring Provider No | string | Referring doctor provider number |
| Notes | string | Free text notes |

### Billing scenarios included in mock data

1. **Standard private billing** — patient pays gap above Medicare benefit (most common)
2. **Bulk billing** — pensioners/concession, Medicare benefit accepted as full payment
3. **DVA billing** — 135% of schedule fee, paid by DVA directly
4. **ECLIPSE No-Gap** — private insurer covers full gap, patient pays nothing above Medicare
5. **ECLIPSE Known-Gap** — patient pays agreed gap amount, insurer pays remainder
6. **Rejected claim** — invalid referral, needs rebilling (revenue leakage flag)
7. **Partial payment** — Medicare processed but patient gap unpaid (outstanding debt)
8. **Multiple items same appointment** — consultation + procedure on same day
9. **Telehealth billing** — video consultation using telehealth MBS item

### MBS items in mock data

| Item | Description | Schedule Fee | Common scenario |
|------|-------------|-------------|-----------------|
| 110 | Initial consultation - consultant physician | $178.70 | New patient first visit |
| 116 | Subsequent attendance - consultant physician | $89.35 | Follow-up visit |
| 55126 | Transthoracic echocardiography | $327.85 | Standard echo |
| 55141 | Exercise stress echocardiography | $448.10 | Stress echo |
| 11700 | ECG - 12 lead | $34.20 | Routine ECG |
| 91824 | Telehealth video - consultant physician | $89.35 | Video follow-up |

---

## Adapter Design Notes

### Data relationships across APIs
```
Appointment (Healthcare API)
  ├── Patient (Healthcare API, nested)
  ├── Practitioner (Bookings API)
  ├── Location (Bookings API)
  ├── AppointmentType (Bookings API)
  ├── Referral (Bookings API)
  ├── Letter(s) (Letters API, linked via appointment_id)
  └── Invoice(s) (Billing CSV, linked via appointment_id)
```

### The adapter must handle
1. **JSON responses** from three REST APIs (Healthcare, Bookings, Letters)
2. **CSV parsing** for billing data export
3. **Cross-referencing** between data sources via shared IDs (patient_id, appointment_id)
4. **Date/timezone handling** — all timestamps are AEST/AEDT (Australia/Sydney)
5. **Pagination** — meta block contains page/per_page for large result sets
6. **Null handling** — many fields are nullable (actual_start on future appointments, dva_file_number on non-DVA patients, etc.)

### What the adapter strips before passing downstream
- Patient names, addresses, contact details (replaced with patient_id only)
- Medicare numbers, DVA file numbers, IHI
- Emergency contact details
- Referring doctor personal details (keep provider_number and practice_name for referral source analysis)

De-identification happens at the adapter boundary. Everything downstream works with IDs and aggregate counts only.
