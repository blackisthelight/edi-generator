# edi-generator

A command-line tool for generating sample HIPAA EDI X12 5010 files used in healthcare claims processing and workers' compensation managed care.

Built for developers who need realistic test data for building EDI parsers, importers, and integration pipelines — without access to production files.

## Quick Start

```bash
# No dependencies — just Python 3
python3 edi_generator.py --type 837P --pretty

# Save to file
python3 edi_generator.py --type 835 --claims 50 --output remittance.edi

# Generate all 6 transaction types at once
python3 edi_generator.py --type all --output-dir ./samples

# Limit to a specific One Call line of business
python3 edi_generator.py --type 837P --lob PT --claims 10 --pretty
```

## Supported Transaction Types

| Type | Name | Direction | Description |
|------|------|-----------|-------------|
| `837P` | Professional Claim | Provider → Payer/MCO | Claims for services rendered, with CPT codes, ICD-10 diagnoses, and WC claim numbers |
| `835` | Remittance Advice | Payer → Provider | Payment/EOB with claim-level and service-level adjudication and adjustment reason codes |
| `270` | Eligibility Inquiry | Provider/MCO → Payer | Batch eligibility checks for multiple subscribers |
| `271` | Eligibility Response | Payer → Provider/MCO | Coverage status, copays, deductibles, visit limits, out-of-pocket maximums |
| `278` | Authorization Request | Provider → MCO | Prior auth requests for PT, OT, imaging, surgery with visit counts and date ranges |
| `999` | Acknowledgment | Receiver → Sender | Receipt confirmation with accept/reject status and error detail |

## CLI Options

```
python3 edi_generator.py [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--type TYPE` | `-t` | `837P`, `835`, `270`, `271`, `278`, `999`, or `all` (default: `837P`) |
| `--claims N` | `-n` | Number of records to generate (default: random) |
| `--output FILE` | `-o` | Write to file instead of stdout |
| `--output-dir DIR` | `-d` | Output directory for `--type all` |
| `--pretty` | `-p` | Newlines between segments for readability |
| `--seed N` | `-s` | Random seed for reproducible output |
| `--lob NAME` | `-l` | Limit to a One Call line of business (see below) |

## Generating Beefy Files

Every transaction type scales with `--claims`. No upper limit.

```bash
# Small — quick parser development
python3 edi_generator.py --type 837P --claims 2 --pretty --seed 1

# Medium — realistic daily batch
python3 edi_generator.py --type 835 --claims 50 --output batch.edi

# Large — stress testing
python3 edi_generator.py --type 271 --claims 500 --output load_test.edi  # ~311 KB

# All types, 100 records each
python3 edi_generator.py --type all --claims 100 --output-dir ./test_data
```

| `--claims` | 837P | 835 | 270 | 271 | 278 | 999 |
|------------|------|-----|-----|-----|-----|-----|
| 2 | ~1 KB | ~1 KB | ~0.5 KB | ~2 KB | ~1 KB | ~0.3 KB |
| 50 | ~22 KB | ~15 KB | ~7 KB | ~35 KB | ~23 KB | ~2.5 KB |
| 500 | ~216 KB | ~151 KB | ~60 KB | ~311 KB | ~230 KB | ~25 KB |

## Filtering by Line of Business

Use `--lob` to constrain CPT codes, providers, facilities, diagnoses, and auth service types to a specific One Call Care Management line of business:

| LOB | Name | Example Procedures |
|-----|------|-------------------|
| `PT` | Physical Therapy | 97110, 97140, 97530, 97113 (aquatic), 97750 (FCE) |
| `OT` | Occupational Therapy | 97530, 97535, 97537, 29125 (splinting), 97750 (FCE) |
| `DC` | Chiropractic | 98940, 98941, 98942, 97012 (traction), 97014 (e-stim) |
| `DX` | Diagnostics | 72148 (MRI), 72131 (CT), 73560 (X-ray), 95907 (EMG/NCS) |
| `DME` | Durable Medical Equipment | E0720 (TENS), L1832 (knee orthosis), K0001 (wheelchair) |
| `HH` | Home Health / Complex Care | 99341 (home visit), S9123 (RN), T1030 (nursing per diem) |
| `DENTAL` | Dental | D2740 (crown), D3310 (root canal), D7140 (extraction) |
| `TRANSPORT` | Transportation | A0100 (ambulance), A0120 (wheelchair van), T2003 (per trip) |
| `LANGUAGE` | Language / Interpreter | T1013 (per 15 min), T1012 (per encounter) |

```bash
# PT-only claims
python3 edi_generator.py --type 837P --lob PT --claims 10 --pretty

# Diagnostics auth requests
python3 edi_generator.py --type 278 --lob DX --claims 5 --pretty

# All types, scoped to DME
python3 edi_generator.py --type all --lob DME --output-dir ./dme_samples
```

Without `--lob`, the generator uses the full cross-LOB data pool.

## Sample Data

The generator uses randomized but realistic data appropriate for workers' compensation managed care:

**Payers:** Travelers, Hartford Financial, Liberty Mutual, Sedgwick CMS, Gallagher Bassett, Zurich, Employers Holdings

**Managed Care Orgs:** One Call Care Management, Coventry WC, CorVel Corporation, First Health Network

**Providers:** MD, DO, DC, PT, OT, DPM, PhD specialists at orthopedic centers, rehab clinics, imaging centers, surgical centers

**CPT Codes:** Office visits (99213/99214), PT/OT (97110/97140/97530), MRI (72148/72141/73721), injections (64483/20610), surgery (27447 TKR, 29881 knee scope), chiropractic (98940/98941)

**ICD-10 Diagnoses:** Lumbar/cervical radiculopathy, knee sprains, rotator cuff tears, disc degeneration, ankle sprains, chronic pain, ACL injuries, wrist fractures

## Other Docs in This Repo

| File | Purpose |
|------|---------|
| [`USAGE.md`](USAGE.md) | Detailed usage guide with segment-level documentation for each transaction type |
| [`EDI_SPEC.md`](EDI_SPEC.md) | EDI X12 5010 parsing specification — everything you need to build an importer (delimiter detection, envelope structure, HL hierarchies, loop/segment maps, state machine approach, validation rules, edge cases, code tables) |

## Example Output

```
$ python3 edi_generator.py --type 278 --claims 1 --pretty --seed 42
```

```
ISA*00*          *00*          *ZZ*COASTALPHYSICAL*ZZ*CORVELCORPORATI*260205*1137*^*00501*397478787*0*T*:~
GS*HI*COASTALPHYSICAL*CORVELCORPORATI*20260205*1137*5821*X*005010X217~
ST*278*3433*005010X217~
BHT*0007*13*6525808631*20260205*1137~
HL*1**20*1~
NM1*X3*2*CORVEL CORPORATION*****46*CORVEL~
HL*2*1*21*1~
NM1*1P*1*BROWN*PATRICIA*PT***XX*1117550026~
REF*EI*930086875~
N3*111 BIRCH CT~
N4*DALLAS*TX*75201~
PER*IC*PATRICIA BROWN*TE*5555918715~
HL*3*2*22*1~
NM1*IL*1*MARTINEZ*SARAH*L***MI*VQW570220212~
DMG*D8*19850622*F~
NM1*PR*2*TRAVELERS INSURANCE*****PI*61425~
HL*4*3*EV*0~
UM*HS*I**11~
HI*BK:S83511A~
HSD*VS*24*DA*53*7~
DTP*472*RD8*20260219-20260413~
SV1*HC:97530*40.00*UN*1~
SE*21*3433~
GE*1*5821~
IEA*1*397478787~
```

## License

MIT
