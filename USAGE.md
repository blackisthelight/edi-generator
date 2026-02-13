# Healthcare EDI X12 5010 File Generator — Usage Guide

A command-line tool for generating sample HIPAA EDI X12 5010 transaction sets used
in healthcare claims processing and workers' compensation managed care workflows.

## Quick Start

```bash
# Generate a professional claim (837P) and print to stdout
python3 edi_generator.py --type 837P

# Human-readable with newlines between segments
python3 edi_generator.py --type 835 --pretty

# Save to file with 20 claims
python3 edi_generator.py --type 835 --claims 20 --output remittance.edi

# Generate all transaction types at once
python3 edi_generator.py --type all --output-dir ./samples

# Reproducible output
python3 edi_generator.py --type 271 --seed 42 --pretty

# Limit to a specific line of business
python3 edi_generator.py --type 837P --lob PT --claims 10 --pretty
```

No dependencies required — pure Python 3 standard library.

---

## Transaction Types

| Type | Name | Direction | What It Does |
|------|------|-----------|-------------|
| `837P` | Professional Claim | Provider -> Payer/MCO | Submit claims for services rendered to injured workers |
| `835` | Remittance Advice | Payer -> Provider | Explain how claims were adjudicated and what was paid |
| `270` | Eligibility Inquiry | Provider/MCO -> Payer | Check if a patient has active workers' comp coverage |
| `271` | Eligibility Response | Payer -> Provider/MCO | Respond with coverage status, benefits, copays, limits |
| `278` | Auth Request | Provider -> MCO | Request prior authorization for PT, imaging, surgery, etc. |
| `999` | Acknowledgment | Receiver -> Sender | Confirm receipt and validity of any of the above |

---

## CLI Reference

```
python3 edi_generator.py [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--type TYPE` | `-t` | Transaction type: `837P`, `835`, `270`, `271`, `278`, `999`, or `all` |
| `--output FILE` | `-o` | Write output to file (default: stdout). Ignored with `--type all`. |
| `--output-dir DIR` | `-d` | Output directory for `--type all` (default: current directory) |
| `--claims N` | `-n` | Number of claims/subscribers/records to include |
| `--pretty` | `-p` | Add newlines between segments for readability |
| `--seed N` | `-s` | Random seed for reproducible output |
| `--lob NAME` | `-l` | Limit data to a specific line of business (see section below) |

---

## Controlling File Size (the `--claims` flag)

Every transaction type supports the `--claims` / `-n` flag. Here's what it controls
and what default ranges you can expect:

| Type | `--claims` controls | Default (random) | Example for beefy file |
|------|---------------------|-------------------|------------------------|
| `837P` | Number of patient claims (each with 1-4 service lines) | 3-10 | `--claims 500` (~216 KB) |
| `835` | Number of adjudicated claims (each with 1-3 SVC lines) | 5-15 | `--claims 500` (~151 KB) |
| `270` | Number of subscriber eligibility inquiries | 3-10 | `--claims 200` (~30 KB) |
| `271` | Number of subscriber eligibility responses (with full benefit detail) | 3-10 | `--claims 500` (~311 KB) |
| `278` | Number of auth requests (each with 1-3 procedures) | 3-8 | `--claims 200` (~92 KB) |
| `999` | Number of transaction sets being acknowledged | 5-15 | `--claims 100` (~6 KB) |

### Examples at different scales

```bash
# Small — quick testing
python3 edi_generator.py --type 837P --claims 2 --pretty

# Medium — realistic batch
python3 edi_generator.py --type 835 --claims 50 --output medium_batch.edi

# Large — stress testing / load testing
python3 edi_generator.py --type 837P --claims 1000 --output big_claims.edi

# All types, beefy
python3 edi_generator.py --type all --claims 100 --output-dir ./large_samples
```

There is no upper limit on `--claims`. The tool can generate files with thousands
of records if needed, limited only by memory.

---

## Filtering by Line of Business (the `--lob` flag)

Use `--lob` / `-l` to constrain generated data to a specific line of business.
When active, CPT/HCPCS codes, provider names,
facility names, ICD-10 diagnoses, auth service types, and place of service codes
are all scoped to that LOB.

| LOB | Name | What It Generates |
|-----|------|-------------------|
| `PT` | Physical Therapy | Therapeutic exercises, manual therapy, gait training, aquatic therapy, work hardening |
| `OT` | Occupational Therapy | ADL training, work reintegration, splinting, hand therapy, FCE |
| `DC` | Chiropractic | Spinal manipulation (1-5 regions), traction, e-stim, therapeutic exercises |
| `DX` | Diagnostics | MRI, CT, X-ray, ultrasound, EMG/NCS studies |
| `DME` | Durable Medical Equipment | TENS units, walkers, wheelchairs, orthotics, CPAP, oxygen |
| `HH` | Home Health / Complex Care | Home visits (RN/LPN), wound care, home PT/OT, nursing per diem |
| `DENTAL` | Dental | Evaluations, radiographs, restorations, crowns, root canals, extractions |
| `TRANSPORT` | Transportation | Non-emergency ambulance, wheelchair van, mileage, waiting time |
| `LANGUAGE` | Language / Interpreter | Interpreter services (per 15 min or per encounter), translation |

### Examples

```bash
# PT-only claims with specific provider/facility/CPT data
python3 edi_generator.py --type 837P --lob PT --claims 10 --pretty

# Diagnostics auth requests (MRI, CT, EMG)
python3 edi_generator.py --type 278 --lob DX --claims 5 --pretty

# DME remittance advice
python3 edi_generator.py --type 835 --lob DME --claims 20 --output dme_remittance.edi

# All types scoped to chiropractic
python3 edi_generator.py --type all --lob DC --output-dir ./dc_samples

# Combine with --seed for reproducibility
python3 edi_generator.py --type 278 --lob PT --claims 3 --seed 42 --pretty
```

Without `--lob`, the generator uses the full cross-LOB data pool (all CPT codes,
all provider types, etc.), which is the default behavior.

### What `--lob` constrains

| Data Pool | Without `--lob` | With `--lob PT` (example) |
|-----------|-----------------|---------------------------|
| CPT codes | All 18 (office visits, PT, OT, MRI, surgery, chiro) | PT-specific (97110, 97140, 97530, 97113, etc.) |
| Providers | MD, DO, DC, PT, OT, DPM, PhD | PT, DPT only |
| Facilities | Ortho centers, imaging, surgical centers | PT clinics, aquatic therapy, work hardening |
| ICD-10 | Full range of WC diagnoses | MSK diagnoses common in PT referrals |
| Auth types | PT, OT, MRI, surgery, pain mgmt, chiro, imaging | PT only |
| Place of service | Office, outpatient, ASC, clinic | Office, independent clinic |

---

## What's Inside Each Transaction Type

### 837P — Professional Claim

Each claim includes:
- **BHT**: Transaction purpose and reference number
- **NM1 loops**: Submitter, receiver, billing provider, subscriber, payer
- **SBR**: Subscriber information with `WC` (Workers' Comp) payer responsibility
- **CLM**: Claim with total charges, place of service (office, outpatient, ASC, clinic)
- **HI**: ICD-10 diagnosis codes (lumbar radiculopathy, rotator cuff tears, knee sprains, etc.)
- **REF Y4**: Workers' comp claim number
- **SV1/DTP**: Service lines with CPT codes and dates of service

CPT codes include: office visits (99213, 99214), PT/OT (97110, 97140, 97530),
imaging (72148 MRI lumbar, 72141 MRI cervical, 73721 MRI joint), injections
(64483 epidural, 20610 arthrocentesis), and surgeries (27447 TKR, 29881 knee scope).

### 835 — Remittance Advice

Each remittance includes:
- **BPR**: Payment amount, method (ACH), banking details
- **TRN**: Check/EFT trace number
- **N1 loops**: Payer and payee (provider) identification with NPI and TIN
- **CLP**: Claim-level payment with charged vs. paid amounts
- **CAS**: Adjustment reason codes (CO-45: exceeds fee schedule, etc.)
- **SVC**: Service-line detail with per-procedure payment breakdown
- **PLB**: Provider-level balance adjustments

### 270 — Eligibility Inquiry

Each inquiry includes:
- **HL hierarchy**: Payer -> Provider -> Subscriber (multiple subscribers per file)
- **NM1**: Subscriber identification with member ID
- **DMG**: Date of birth
- **DTP 291**: Service date for eligibility check
- **EQ**: Service type codes being inquired about (1-4 per subscriber, including
  medical care, chiropractic, pharmacy, mental health, PT, OT, urgent care, etc.)

### 271 — Eligibility Response

Each response includes:
- **HL hierarchy**: Same as 270 but with response data
- **INS**: Subscriber relationship and status
- **DTP 346**: Plan effective date
- **EB segments** (multiple per subscriber):
  - `EB*1` — Active coverage confirmation with plan name
  - `EB*B` — Co-payment amounts per service type (office visits, PT, chiropractic, etc.)
  - `EB*F` — Visit/frequency limits (e.g., 24 PT visits per year)
  - `EB*G` — Out-of-pocket maximum
  - `EB*C` — Deductible amounts
  - `EB*6` — Inactive coverage (with termination date) for ~15% of subscribers

### 278 — Authorization Request

Each request includes:
- **HL hierarchy**: MCO -> Provider -> Subscriber -> Patient Event
- **NM1**: Provider with NPI, subscriber with member ID, payer
- **UM**: Review type (health services, specialty care, admission review) and
  certification type (initial, renewal, extension)
- **HI**: Diagnosis codes (1-3 per request)
- **HSD**: Requested number of visits and duration
- **DTP 472**: Requested authorization date range
- **REF BB**: Previous authorization number (for renewals/extensions)
- **SV1**: Procedures being requested (1-3 per request)

### 999 — Implementation Acknowledgment

Each acknowledgment includes:
- **AK1**: Functional group being acknowledged (with correct version ID)
- **AK2/IK5**: Per-transaction acceptance status (Accepted / Accepted with Errors / Rejected)
- **IK3**: Segment-level error detail (for errors/rejections) — identifies which segment failed
- **IK4**: Element-level error detail — identifies which data element and error type
- **AK9**: Group-level summary with accepted/rejected counts

~70% of transactions are accepted, ~15% accepted with errors (1-2 IK3/IK4 notes),
~15% rejected (2-4 IK3/IK4 error details).

---

## Sample Data

The generator uses randomized but realistic data pools appropriate for workers'
compensation managed care:

**Payers**: Travelers, Hartford Financial, Liberty Mutual, Sedgwick CMS,
Gallagher Bassett, Zurich, Employers Holdings

**Managed Care Orgs**: Acme Managed Care, Coventry WC, CorVel Corporation,
First Health Network

**Providers**: MD, DO, DC, PT, OT, DPM, PhD specialists at facilities like
Premier Orthopedic Center, Regional Rehabilitation Clinic, Advanced Imaging Associates

**Diagnoses**: Lumbar/cervical radiculopathy, knee sprains, shoulder injuries,
disc degeneration, ankle sprains, chronic pain, rotator cuff tears, ACL sprains,
wrist fractures, bursitis

---

## EDI File Structure Primer

Every generated file follows the ANSI X12 5010 format:

```
ISA...~          <- Interchange envelope start (sender/receiver IDs)
  GS...~         <- Functional group start (transaction type)
    ST...~        <- Transaction set start
      [body]~     <- The actual healthcare data
    SE...~        <- Transaction set end (segment count)
  GE...~          <- Functional group end
IEA...~           <- Interchange envelope end
```

- `*` separates data elements within a segment
- `~` terminates each segment
- `:` separates sub-elements (composite data elements)
- `^` is the repetition separator (5010-specific)

The `--pretty` flag adds newlines between segments for human readability.
Without it, the entire file is a continuous string (as real EDI systems expect).
