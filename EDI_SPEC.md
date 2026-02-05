# EDI X12 5010 File Format Specification

A practical reference for implementing an EDI X12 parser/importer, focused on
the healthcare transaction types used in workers' comp and managed care.

---

## Table of Contents

1. [Delimiter Detection](#1-delimiter-detection)
2. [Envelope Structure](#2-envelope-structure)
3. [Segment Anatomy](#3-segment-anatomy)
4. [Hierarchical Levels (HL Loops)](#4-hierarchical-levels-hl-loops)
5. [Loop Structure & Parser State](#5-loop-structure--parser-state)
6. [Transaction Type: 837P (Professional Claim)](#6-transaction-type-837p-professional-claim)
7. [Transaction Type: 835 (Remittance Advice)](#7-transaction-type-835-remittance-advice)
8. [Transaction Type: 270 (Eligibility Inquiry)](#8-transaction-type-270-eligibility-inquiry)
9. [Transaction Type: 271 (Eligibility Response)](#9-transaction-type-271-eligibility-response)
10. [Transaction Type: 278 (Authorization Request)](#10-transaction-type-278-authorization-request)
11. [Transaction Type: 999 (Implementation Acknowledgment)](#11-transaction-type-999-implementation-acknowledgment)
12. [Parser Implementation Strategy](#12-parser-implementation-strategy)
13. [Validation Rules](#13-validation-rules)
14. [Edge Cases & Gotchas](#14-edge-cases--gotchas)
15. [Common Code Tables](#15-common-code-tables)

---

## 1. Delimiter Detection

**The ISA segment is always exactly 106 characters.** This fixed width is the key
to bootstrapping any EDI parser — you extract the delimiters from known positions
before parsing anything else.

### ISA fixed positions (0-indexed)

```
Position  0-2:    "ISA" (literal)
Position  3:      ELEMENT SEPARATOR        (usually *)
Position  104:    REPETITION SEPARATOR     (usually ^ in 5010, U in 4010)
Position  105:    SEGMENT TERMINATOR       (usually ~)
```

The **sub-element (component) separator** is the value of ISA16, which is the
last data element before the segment terminator. In practice:

```
ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     *260205*1337*^*00501*000000001*0*T*:~
   ^                                                                          ^    ^                ^ ^
   |                                                                          |    |                | |
   element_sep = '*' (char at position 3)                                     |    |                | segment_term = '~' (char at 105)
                                                          repetition_sep = '^' (char at 104)        |
                                                                                                    sub_element_sep = ':' (ISA16 value)
```

### Delimiter extraction algorithm

```python
def detect_delimiters(raw: str) -> dict:
    """Extract delimiters from the ISA segment (first 106 chars)."""
    assert raw[:3] == "ISA", "File must start with ISA"
    return {
        "element_sep":      raw[3],      # Almost always *
        "segment_term":     raw[105],    # Almost always ~
        "sub_element_sep":  raw[104],    # Usually : (value of ISA16)
        "repetition_sep":   raw[82],     # Usually ^ for 5010 (ISA11)
    }
```

> **Important:** Do NOT hardcode `*`, `~`, `:`. Always detect from the ISA.
> Some trading partners use `|` as element separator or `\n` as segment terminator.

### Common delimiter sets

| Variant | Element | Segment | Sub-element | Repetition |
|---------|---------|---------|-------------|------------|
| Standard | `*` | `~` | `:` | `^` |
| Pipe-delimited | `\|` | `~` | `:` | `^` |
| Newline-terminated | `*` | `\n` | `:` | `^` |
| Legacy 4010 | `*` | `~` | `:` | `U` (not used) |

---

## 2. Envelope Structure

Every EDI file is a nested set of envelopes:

```
ISA ... ~                          ← Interchange Header (one per file)
  GS ... ~                         ← Functional Group Header (one per txn type)
    ST ... ~                       ← Transaction Set Header
      [transaction body segments]
    SE*{count}*{st_control} ~      ← Transaction Set Trailer
  GE*{num_txn_sets}*{gs_control} ~ ← Functional Group Trailer
IEA*{num_groups}*{isa_control} ~   ← Interchange Trailer
```

### Nesting rules

- One **ISA/IEA** per file (interchange). Each interchange has a unique
  9-digit control number (ISA13 = IEA02).
- One or more **GS/GE** groups per interchange. Each groups transactions
  of the same type (e.g., all 837s, all 835s). GS06 = GE02.
- One or more **ST/SE** transaction sets per group. ST02 = SE02.
  SE01 is the count of segments from ST to SE inclusive.

### Parsing order

```
1. Read ISA → extract delimiters → read until IEA
2. Within ISA/IEA → read GS segments → group by GS01 (functional ID code)
3. Within GS/GE → read ST segments → parse each transaction body
4. Verify trailer counts match (SE01, GE01, IEA01)
```

### ISA element layout (all fields are fixed-width, space-padded)

| Pos | ID    | Name                    | Width | Notes |
|-----|-------|-------------------------|-------|-------|
| 01  | ISA01 | Auth Info Qualifier     | 2     | Usually "00" |
| 02  | ISA02 | Auth Information        | 10    | Usually spaces |
| 03  | ISA03 | Security Info Qualifier | 2     | Usually "00" |
| 04  | ISA04 | Security Information    | 10    | Usually spaces |
| 05  | ISA05 | Sender ID Qualifier     | 2     | "ZZ"=mutually defined, "01"=DUNS |
| 06  | ISA06 | Sender ID               | 15    | Right-padded with spaces |
| 07  | ISA07 | Receiver ID Qualifier   | 2     | Same codes as ISA05 |
| 08  | ISA08 | Receiver ID             | 15    | Right-padded with spaces |
| 09  | ISA09 | Date                    | 6     | YYMMDD |
| 10  | ISA10 | Time                    | 4     | HHMM |
| 11  | ISA11 | Repetition Separator    | 1     | "^" for 5010 |
| 12  | ISA12 | Version                 | 5     | "00501" for 5010 |
| 13  | ISA13 | Control Number          | 9     | Must match IEA02 |
| 14  | ISA14 | Ack Requested           | 1     | "0" or "1" |
| 15  | ISA15 | Usage Indicator         | 1     | "T"=test, "P"=production |
| 16  | ISA16 | Sub-element Separator   | 1     | Usually ":" |

### GS element layout

| Pos | Name                    | Notes |
|-----|-------------------------|-------|
| 01  | Functional ID Code      | HC=837, HP=835, HS=270, HB=271, HI=278, FA=999 |
| 02  | Application Sender Code | |
| 03  | Application Receiver    | |
| 04  | Date                    | YYYYMMDD |
| 05  | Time                    | HHMM |
| 06  | Group Control Number    | Must match GE02 |
| 07  | Responsible Agency      | "X" for X12 |
| 08  | Version/Release/Industry| e.g., "005010X222A1" for 837P |

### GS01 → Transaction type mapping

| GS01 | ST ID | Transaction Type |
|------|-------|-----------------|
| HC   | 837   | Health Care Claim |
| HP   | 835   | Claim Payment/Remittance Advice |
| HS   | 270   | Eligibility Inquiry |
| HB   | 271   | Eligibility Response |
| HI   | 278   | Health Care Services Review |
| FA   | 999   | Implementation Acknowledgment |

### GS08 version strings (5010)

| Transaction | GS08 / ST03 |
|-------------|-------------|
| 837P (Professional) | 005010X222A1 |
| 837I (Institutional) | 005010X223A3 |
| 835 | 005010X221A1 |
| 270/271 | 005010X279A1 |
| 278 | 005010X217 |
| 999 | 005010X231A1 |

---

## 3. Segment Anatomy

A segment is a line of data consisting of:

```
SEGMENT_ID*ELEMENT1*ELEMENT2*...*ELEMENTN~
```

### Rules

- Segment ID is 2-3 alphanumeric characters (e.g., `NM1`, `CLM`, `HL`, `ST`)
- Elements are separated by the element separator (usually `*`)
- Trailing empty elements can be omitted:
  `NM1*IL*1*SMITH*JOHN~` is valid even if NM1 has 12 defined positions
- Empty elements are represented by consecutive separators: `**`
- **Composite elements** contain sub-elements separated by the sub-element sep:
  `SV1*HC:99213*150.00*UN*1~`  →  SV1-01 is composite: `HC` (qualifier) + `99213` (code)
- **Repeated elements** (5010) use the repetition separator:
  `EB*1**1^33^35^47~`  →  service type codes 1, 33, 35, 47

### Segment parsing pseudocode

```python
def parse_segment(raw_segment: str, element_sep: str, sub_element_sep: str) -> dict:
    elements = raw_segment.split(element_sep)
    segment_id = elements[0]
    data = []
    for elem in elements[1:]:
        if sub_element_sep in elem:
            data.append(elem.split(sub_element_sep))  # composite
        else:
            data.append(elem)  # simple
    return {"id": segment_id, "elements": data}
```

---

## 4. Hierarchical Levels (HL Loops)

Many healthcare transactions use `HL` segments to establish parent-child
relationships. This is the most important structural concept for parsing
837P, 270, 271, and 278 files.

### HL segment elements

| Pos | Name | Description |
|-----|------|-------------|
| 01  | HL ID | Sequential counter (1, 2, 3...) within the transaction |
| 02  | Parent HL ID | Points to parent HL01 value. Empty for root. |
| 03  | Level Code | Type of this level (see table below) |
| 04  | Child Code | "1" = has children, "0" = leaf node |

### HL level codes

| Code | Meaning | Used in |
|------|---------|---------|
| 20   | Information Source (Payer) | 270, 271, 278 |
| 20   | Billing Provider | 837P |
| 21   | Information Receiver / Requester (Provider) | 270, 271, 278 |
| 22   | Subscriber | 837P, 270, 271, 278 |
| 23   | Dependent | 837P (when patient ≠ subscriber) |
| EV   | Patient Event | 278 |
| S    | Shipment | 856 (not healthcare but included for completeness) |

### HL tree example (837P)

```
HL*1**20*1           ← Billing Provider (root)
  ├─ HL*2*1*22*0     ← Subscriber/Patient #1 (leaf)
  │    └─ CLM, SV1, DTP...  (claim data)
  ├─ HL*3*1*22*0     ← Subscriber/Patient #2 (leaf)
  │    └─ CLM, SV1, DTP...
  └─ HL*4*1*22*0     ← Subscriber/Patient #3 (leaf)
       └─ CLM, SV1, DTP...
```

### HL tree example (278)

```
HL*1**20*1           ← Utilization Management Org (root)
  ├─ HL*2*1*21*1     ← Requesting Provider
  │  ├─ HL*3*2*22*1  ← Subscriber
  │  │  └─ HL*4*3*EV*0  ← Patient Event (leaf)
  │  │       └─ UM, HI, HSD, DTP, SV1...
  ├─ HL*5*1*21*1     ← Another Provider
  │  ├─ HL*6*5*22*1  ← Subscriber
  │  │  └─ HL*7*6*EV*0  ← Patient Event
  ...
```

### Parsing HL hierarchies

```python
def build_hl_tree(segments):
    """Build a tree from HL segments. Each HL node owns all segments
    until the next HL (or end of transaction)."""
    nodes = {}  # hl_id -> {parent_id, level_code, segments: [...]}
    current_hl = None
    for seg in segments:
        if seg["id"] == "HL":
            hl_id = seg["elements"][0]
            parent_id = seg["elements"][1] or None
            level_code = seg["elements"][2]
            nodes[hl_id] = {
                "parent": parent_id,
                "level": level_code,
                "segments": []
            }
            current_hl = hl_id
        elif current_hl:
            nodes[current_hl]["segments"].append(seg)
    return nodes
```

---

## 5. Loop Structure & Parser State

Loops are repeating groups of segments. Unlike HL levels (which have explicit
parent pointers), most loops are **implicit** — you detect them by the segment
that triggers the loop.

### How loops work

- A loop starts when its **trigger segment** appears
- A loop ends when: the trigger segment appears again (new iteration),
  or a segment from a parent/sibling loop appears
- Loops can nest inside each other

### Loop identification pattern

```
Loop 2000A starts at → HL (level 20)
  Loop 2010AA starts at → NM1 (qualifier "85" = billing provider)
  Loop 2010AB starts at → NM1 (qualifier "87" = pay-to provider)
Loop 2000B starts at → HL (level 22)
  Loop 2010BA starts at → NM1 (qualifier "IL" = subscriber)
  Loop 2010BB starts at → NM1 (qualifier "PR" = payer)
  Loop 2300 starts at → CLM
    Loop 2400 starts at → LX
```

### State machine approach

The most reliable way to parse loops is a state machine where the current
state determines which segments/loops are valid next:

```python
# Simplified 837P state machine transitions
TRANSITIONS = {
    "HEADER":    {"BHT": "HEADER", "NM1_41": "1000A", "NM1_40": "1000B"},
    "1000A":     {"PER": "1000A", "NM1_40": "1000B"},
    "1000B":     {"HL_20": "2000A"},
    "2000A":     {"PRV": "2000A", "NM1_85": "2010AA", "NM1_87": "2010AB"},
    "2010AA":    {"N3": "2010AA", "N4": "2010AA", "REF": "2010AA", "HL_22": "2000B"},
    "2000B":     {"SBR": "2000B", "NM1_IL": "2010BA"},
    "2010BA":    {"N3": "2010BA", "N4": "2010BA", "DMG": "2010BA", "NM1_PR": "2010BB"},
    "2010BB":    {"CLM": "2300"},
    "2300":      {"DTP": "2300", "REF": "2300", "HI": "2300", "LX": "2400",
                  "HL_22": "2000B"},  # new subscriber = new loop
    "2400":      {"SV1": "2400", "DTP": "2400", "LX": "2400",
                  "CLM": "2300", "HL_22": "2000B"},
}
```

> **Key insight:** For NM1 segments, the **entity identifier code** (NM1-01)
> determines which loop you're in. `NM1*85` = billing provider (Loop 2010AA),
> `NM1*IL` = subscriber (Loop 2010BA), `NM1*PR` = payer (Loop 2010BB).

---

## 6. Transaction Type: 837P (Professional Claim)

**Direction:** Provider → Payer/MCO

### Loop structure

```
ST  Transaction Set Header
  BHT  Beginning of Hierarchical Transaction
  Loop 1000A  Submitter
    NM1*41  Submitter Name
    PER     Submitter Contact
  Loop 1000B  Receiver
    NM1*40  Receiver Name
  Loop 2000A  Billing Provider (HL level 20)
    HL
    PRV  Provider Specialty (taxonomy code)
    Loop 2010AA  Billing Provider Name/Address
      NM1*85  Billing Provider Name (NPI in NM1-09)
      N3      Address
      N4      City/State/ZIP
      REF*EI  Tax ID
    Loop 2000B  Subscriber (HL level 22) [REPEATS per patient]
      HL
      SBR  Subscriber Info (SBR-09: "WC" = Workers Comp)
      Loop 2010BA  Subscriber Name
        NM1*IL  Subscriber Name + Member ID
        N3      Address
        N4      City/State/ZIP
        DMG     Demographics (DOB, gender)
      Loop 2010BB  Payer
        NM1*PR  Payer Name + Payer ID
      Loop 2300  Claim [REPEATS per claim]
        CLM  Claim Info (claim ID, total charge, place of service)
        DTP*431  Statement Date
        REF*D9   Claim ID Reference
        REF*Y4   Workers' Comp Claim Number
        HI   Diagnosis Codes (ICD-10)
        Loop 2400  Service Line [REPEATS per procedure]
          LX   Line Counter
          SV1  Professional Service (CPT code, charge, units)
          DTP*472  Date of Service
SE  Transaction Set Trailer
```

### Key segments to extract

| Segment | Key Elements | What to capture |
|---------|-------------|-----------------|
| BHT | 02=purpose, 06=type | "00"=original, "CH"=chargeable |
| NM1*85 | 03=last, 04=first, 09=NPI | Billing provider identification |
| SBR | 01=payer responsibility, 09=claim filing indicator | "WC" = workers comp |
| NM1*IL | 03=last, 04=first, 09=member ID | Patient/subscriber |
| CLM | 01=claim ID, 02=total charge, 05=place of service (composite) | Core claim record |
| HI | 01+=diagnosis codes (composite, BK: prefix=principal, BF:=additional) | ICD-10 codes |
| SV1 | 01=procedure code (composite HC:CPT), 02=charge, 03=unit type, 04=qty | Service line |
| DTP*472 | 03=date | Date of service |
| REF*Y4 | 02=WC claim number | Workers comp claim link |

### CLM-05 composite (Place of Service)

```
CLM*123456*250.00***11:B:1~
                    ^^ ^ ^
                    |  | └─ Claim frequency code (1=original)
                    |  └─── Facility code qualifier (B=place of service)
                    └────── Place of service code (11=office, 22=outpatient, etc.)
```

### HI composite (Diagnosis Codes)

```
HI*BK:M5416*BF:S8350XA~
   ^^ ^^^^^ ^^ ^^^^^^^
   |  |     |  └─ Additional diagnosis ICD-10
   |  |     └──── BF = Additional diagnosis qualifier
   |  └────────── Principal diagnosis ICD-10 code
   └───────────── BK = Principal diagnosis qualifier
```

---

## 7. Transaction Type: 835 (Remittance Advice)

**Direction:** Payer → Provider

### Loop structure

```
ST  Transaction Set Header
  BPR  Financial Information (payment amount, method, banking)
  TRN  Check/EFT Trace Number
  DTM*405  Production Date
  Loop 1000A  Payer
    N1*PR  Payer Name
    N3     Address
    N4     City/State/ZIP
    REF*2U Payer ID
    PER*BL Contact
  Loop 1000B  Payee (Provider)
    N1*PE  Payee Name + NPI
    N3     Address
    N4     City/State/ZIP
    REF*TJ Tax ID
  Loop 2100  Claim Payment [REPEATS per claim]
    CLP  Claim Payment Info
    CAS  Claim-level Adjustments
    NM1*QC  Patient Name + Member ID
    DTM*232  Statement From Date
    DTM*233  Statement To Date
    Loop 2110  Service Payment [REPEATS per service line]
      SVC  Service Payment Info
      DTM*472  Service Date
      CAS  Line-level Adjustments
      AMT*B6  Allowed Amount
  PLB  Provider-level Adjustments (optional, at end)
SE  Transaction Set Trailer
```

### Key segments to extract

| Segment | Key Elements | What to capture |
|---------|-------------|-----------------|
| BPR | 01=handling code, 02=total payment, 03=credit/debit, 04=payment method | C=credit, D=debit; ACH vs CHK |
| TRN | 02=check/EFT number, 03=originator ID | Trace for reconciliation |
| CLP | 01=claim ID, 02=status code, 03=total charged, 04=total paid, 06=filing indicator, 07=payer claim number | Core remittance record |
| CAS | 01=adjustment group, 02=reason code, 03=amount | CO=contractual, PR=patient resp, OA=other |
| SVC | 01=procedure code (composite), 02=charged, 03=paid | Per-service adjudication |
| AMT*B6 | 02=amount | Allowed amount for the service |
| PLB | 01=provider ID, 03=adjustment type (composite), 04=amount | Provider-level offsets |

### CLP-02 Claim Status Codes

| Code | Meaning |
|------|---------|
| 1 | Processed as Primary |
| 2 | Processed as Secondary |
| 3 | Processed as Tertiary |
| 4 | Denied |
| 19 | Processed as Primary, Forwarded to Additional Payer(s) |
| 20 | Processed as Secondary, Forwarded to Additional Payer(s) |
| 22 | Reversal of Previous Payment |

### CAS Adjustment Group Codes

| Code | Meaning | Who pays |
|------|---------|----------|
| CO | Contractual Obligations | Write-off (nobody) |
| PR | Patient Responsibility | Patient |
| OA | Other Adjustments | Varies |
| PI | Payer Initiated Reductions | Payer decision |
| CR | Correction and Reversals | N/A |

### CAS Reason Codes (common in WC)

| Code | Meaning |
|------|---------|
| 1 | Deductible |
| 2 | Coinsurance |
| 3 | Copayment |
| 45 | Charges exceed fee schedule/maximum allowable |
| 59 | Charges are based on maximum allowed |
| 97 | Payment adjusted based on authorization |
| 253 | Sequestration adjustment |

---

## 8. Transaction Type: 270 (Eligibility Inquiry)

**Direction:** Provider/MCO → Payer

### Loop structure

```
ST  Transaction Set Header
  BHT  Beginning of Hierarchical Transaction (BHT-02: "13" = request)
  Loop 2000A  Information Source (HL level 20)
    HL
    NM1*PR  Payer Name + Payer ID
  Loop 2000B  Information Receiver (HL level 21)
    HL
    NM1*1P  Provider/Facility Name + NPI
    REF*EI  Tax ID
  Loop 2000C  Subscriber (HL level 22) [REPEATS per patient]
    HL
    TRN  Trace Number (for matching response)
    NM1*IL  Subscriber Name + Member ID
    DMG  Demographics
    DTP*291  Service Date
    EQ   Eligibility Inquiry [REPEATS per service type]
SE  Transaction Set Trailer
```

### EQ Service Type Codes (common)

| Code | Service Type |
|------|-------------|
| 30 | Health Benefit Plan Coverage (general) |
| 1  | Medical Care |
| 33 | Chiropractic |
| 35 | Dental |
| 47 | Hospital |
| 86 | Emergency Services |
| 88 | Pharmacy |
| 98 | Professional (Physician) Visit |
| AL | Vision |
| MH | Mental Health |
| UC | Urgent Care |
| PT | Physical Therapy |
| OT | Occupational Therapy |

---

## 9. Transaction Type: 271 (Eligibility Response)

**Direction:** Payer → Provider/MCO

### Loop structure

```
ST  Transaction Set Header
  BHT  (BHT-02: "11" = response)
  Loop 2000A  Information Source (HL level 20)
    HL
    NM1*PR  Payer
  Loop 2000B  Information Receiver (HL level 21)
    HL
    NM1*1P  Provider
  Loop 2000C  Subscriber (HL level 22) [REPEATS per patient]
    HL
    TRN  Trace Number (matches 270 request)
    NM1*IL  Subscriber Name + Member ID
    N3     Address
    N4     City/State/ZIP
    DMG    Demographics (DOB, gender)
    INS    Subscriber Relationship & Status
    DTP*346  Plan Effective Date
    DTP*347  Plan Termination Date (if inactive)
    Loop 2110  Eligibility/Benefit [REPEATS - multiple EB per subscriber]
      EB   Eligibility/Benefit Information
SE  Transaction Set Trailer
```

### EB segment — the core of the 271

The EB segment is where all the benefit detail lives. It repeats many times
per subscriber, each time with different information.

| Pos | Name | Description |
|-----|------|-------------|
| 01 | Information Type | 1=Active, 6=Inactive, B=Co-Payment, C=Deductible, F=Limitations, G=Out-of-Pocket, L=Limitations |
| 02 | Coverage Level | IND=Individual, FAM=Family, EMP=Employee |
| 03 | Service Type Code | Same codes as EQ (see table above). Can use repetition sep for multiple: `1^33^35` |
| 04 | Insurance Type | HM=HMO, PP=PPO, etc. |
| 05 | Plan Coverage Description | Free text plan name |
| 06 | Time Period Qualifier | 27=Visit, 29=Year, 23=Calendar Year, 7=Day |
| 07 | Monetary Amount | Dollar amount (copay, deductible, OOP max) |
| 08-12 | Additional qualifiers | Percentage, quantity, authorization info |

### EB patterns to recognize

```
EB*1**30**WC PREFERRED PLAN~              → Active coverage, plan name
EB*6**30**WC PREFERRED PLAN~              → INACTIVE coverage
EB*B*IND*98*HM*WC PLAN*27*25~            → $25 copay for physician visits
EB*C*IND*30*HM*WC PLAN*29*500~           → $500 annual deductible
EB*G*IND*30*HM*WC PLAN*29*5000~          → $5000 out-of-pocket maximum
EB*F*IND*PT*HM*WC PLAN*27***24*23~       → 24 PT visits per calendar year limit
EB*L~                                      → Limitations exist (general flag)
```

### Parser logic for 271

```python
for eb_segment in subscriber_ebs:
    info_type = eb[1]   # Position 01
    if info_type == "1":
        # Active coverage — extract plan name from eb[5]
        status = "ACTIVE"
    elif info_type == "6":
        # Inactive — look for DTP*347 for termination date
        status = "INACTIVE"
    elif info_type == "B":
        # Co-payment — amount in eb[7], service type in eb[3]
        copay = eb[7]
    elif info_type == "C":
        # Deductible — amount in eb[7]
        deductible = eb[7]
    elif info_type == "G":
        # Out-of-pocket max — amount in eb[7]
        oop_max = eb[7]
    elif info_type in ("F", "L"):
        # Limitation — may include visit counts
        if eb[10]:  # quantity
            max_visits = eb[10]
```

---

## 10. Transaction Type: 278 (Authorization Request)

**Direction:** Provider → MCO (e.g., One Call)

### Loop structure

```
ST  Transaction Set Header
  BHT  (BHT-01: "0007", BHT-02: "13" = request)
  Loop 2000A  Utilization Management Org (HL level 20)
    HL
    NM1*X3  MCO/UM Organization Name
  Loop 2000B  Requester/Provider (HL level 21) [REPEATS per provider]
    HL
    NM1*1P  Provider Name + NPI
    REF*EI  Tax ID
    N3/N4   Address
    PER     Contact
    Loop 2000C  Subscriber (HL level 22) [REPEATS per patient]
      HL
      NM1*IL  Subscriber Name + Member ID
      N3/N4   Address
      DMG     Demographics
      NM1*PR  Payer Name + ID
      Loop 2000D  Patient Event (HL level EV) [REPEATS per event]
        HL
        UM   Review/Certification Info
        HI   Diagnosis Codes
        HSD  Requested Services (visits, duration)
        DTP*472  Requested Date Range
        REF*BB  Previous Auth Number (renewals/extensions)
        SV1  Service Lines [REPEATS per procedure]
SE  Transaction Set Trailer
```

### UM segment elements

| Pos | Name | Values |
|-----|------|--------|
| 01 | Review Type | HS=Health Services, SC=Specialty Care, AR=Admission Review |
| 02 | Certification Type | I=Initial, R=Renewal/Recert, E=Extension |
| 03 | Service Type | (usually empty, detail in SV1) |
| 04 | Place of Service | 11=Office, 22=Outpatient, etc. |

### HSD segment elements

| Pos | Name | Description |
|-----|------|-------------|
| 01 | Quantity Qualifier | VS=Visits |
| 02 | Quantity | Number of visits requested |
| 03 | Unit/Measurement | DA=Days |
| 04 | Period Count | Duration in days |
| 05 | Time Period Qualifier | 7=Day |

### DTP*472 Date Range Format

```
DTP*472*RD8*20260301-20260531~
          ^^^ ^^^^^^^^ ^^^^^^^^
          |   |        └─ End date
          |   └────────── Start date
          └────────────── RD8 = date range format
```

---

## 11. Transaction Type: 999 (Implementation Acknowledgment)

**Direction:** Receiver → Sender (acknowledges receipt of any transaction)

### Loop structure

```
ST  Transaction Set Header
  AK1  Functional Group Response Header
  Loop AK2  Transaction Set Response [REPEATS per transaction]
    AK2  Transaction Set Response Header
    Loop IK3  Segment Error [REPEATS per error, only for E/R status]
      IK3  Segment Error Detail
      IK4  Element Error Detail
    IK5  Transaction Set Response Trailer (status)
  AK9  Functional Group Response Trailer (summary)
SE  Transaction Set Trailer
```

### Key segments

| Segment | Elements | Description |
|---------|----------|-------------|
| AK1 | 01=functional ID, 02=GS control#, 03=version | Identifies which group is being acknowledged |
| AK2 | 01=txn set ID, 02=ST control#, 03=version | Identifies which transaction set |
| IK3 | 01=segment ID, 02=position, 04=error code | Which segment had the error |
| IK4 | 01=element position, 04=error code | Which element within the segment |
| IK5 | 01=status | A=Accepted, E=Accepted w/Errors, R=Rejected |
| AK9 | 01=group status, 02=txn sets included, 03=txn sets received, 04=txn sets accepted | A=Accepted, P=Partially, R=Rejected |

---

## 12. Parser Implementation Strategy

### Recommended architecture

```
┌─────────────────┐
│   Raw EDI text   │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Delimiter Detect │  ← Read ISA, extract *, ~, :, ^
└────────┬────────┘
         ▼
┌─────────────────┐
│ Segment Splitter │  ← Split on segment terminator
└────────┬────────┘
         ▼
┌─────────────────┐
│ Element Parser   │  ← Split each segment on element separator
└────────┬────────┘   ← Split composites on sub-element separator
         ▼
┌─────────────────┐
│ Envelope Parser  │  ← Match ISA/IEA, GS/GE, ST/SE pairs
└────────┬────────┘   ← Validate control numbers and counts
         ▼
┌─────────────────┐
│ Transaction      │  ← Route to type-specific parser based on ST-01 / GS-01
│ Type Router      │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Loop/HL Parser   │  ← Build HL tree, detect loop boundaries
└────────┬────────┘   ← Use state machine for loop transitions
         ▼
┌─────────────────┐
│ Domain Objects   │  ← Claims, Patients, Providers, Benefits, etc.
└─────────────────┘
```

### Step-by-step parsing

```python
class EDIParser:
    def parse(self, raw_text: str):
        # Step 1: Detect delimiters from ISA
        delimiters = self.detect_delimiters(raw_text)

        # Step 2: Split into segments (handle whitespace/newlines)
        clean = raw_text.strip()
        segments = clean.split(delimiters["segment_term"])
        segments = [s.strip() for s in segments if s.strip()]

        # Step 3: Parse each segment into elements
        parsed = []
        for seg in segments:
            elements = seg.split(delimiters["element_sep"])
            parsed.append({
                "id": elements[0],
                "elements": elements[1:]
            })

        # Step 4: Extract envelope
        interchanges = self.extract_envelopes(parsed)

        # Step 5: For each transaction set, route to type-specific parser
        for interchange in interchanges:
            for group in interchange["groups"]:
                txn_type = group["functional_id"]  # GS01
                for txn in group["transactions"]:
                    if txn_type == "HC":
                        yield self.parse_837(txn)
                    elif txn_type == "HP":
                        yield self.parse_835(txn)
                    # ... etc
```

---

## 13. Validation Rules

### Envelope validation

| Check | Rule |
|-------|------|
| ISA13 == IEA02 | Interchange control numbers must match |
| GS06 == GE02 | Group control numbers must match |
| ST02 == SE02 | Transaction set control numbers must match |
| SE01 | Must equal actual segment count (ST through SE inclusive) |
| GE01 | Must equal number of ST/SE transaction sets in the group |
| IEA01 | Must equal number of GS/GE groups in the interchange |

### Segment validation

| Rule | Description |
|------|-------------|
| Required segments | ST, SE, BHT (or BPR for 835) must be present |
| HL hierarchy | Every HL02 (parent) must reference a valid HL01 |
| NM1 qualifiers | Entity identifier (NM1-01) must be valid for the loop context |
| Date formats | DTP-02 determines format: D8=YYYYMMDD, RD8=YYYYMMDD-YYYYMMDD |
| Composite integrity | Sub-elements within composites must follow the defined structure |

### Data type codes

| Code | Type | Description |
|------|------|-------------|
| AN | Alphanumeric | Letters, digits, spaces, special chars |
| ID | Identifier | Code from a defined code set |
| N0 | Numeric (0 decimal) | Integer |
| N2 | Numeric (2 decimal) | Implied 2 decimal places (pennies for dollars) |
| DT | Date | YYMMDD or YYYYMMDD |
| TM | Time | HHMM or HHMMSS |
| R | Real | Decimal number |

---

## 14. Edge Cases & Gotchas

### Whitespace and newlines

EDI files may or may not have newlines between segments. Your splitter should:

```python
# Strip whitespace around segments after splitting on terminator
segments = [s.strip() for s in raw.split(seg_term) if s.strip()]
```

Some systems insert `\r\n` or `\n` after the segment terminator. Others use
the newline itself *as* the segment terminator. Always detect from ISA[105].

### Trailing element separators

Trailing empty elements are usually omitted, but some systems include them:

```
NM1*IL*1*SMITH*JOHN****MI*123456~     ← Normal: trailing empties omitted
NM1*IL*1*SMITH*JOHN*****MI*123456*~   ← Some systems: trailing * present
```

Your parser should handle both. Trim trailing empty strings from the elements array.

### ISA fixed-width gotcha

The ISA segment is the ONLY fixed-width segment. All other segments are variable
width with delimiters. Don't try to parse ISA by splitting on `*` — the element
separator hasn't been confirmed yet. Parse it positionally first, then switch to
delimiter-based parsing for everything else.

Actually, in practice you CAN split ISA on the detected element separator (char at
position 3), because the ISA *does* use delimiters between fields — the fields are
just also fixed-width. Both approaches work. The important thing is to get the
delimiters from the fixed positions first.

### Multiple transaction sets in one file

A single file can contain multiple ST/SE pairs within one GS/GE group, and
multiple GS/GE groups within one ISA/IEA. Don't assume one transaction per file.

```
ISA...~
  GS*HC...~
    ST*837*0001~  ← Transaction 1
    ...
    SE*50*0001~
    ST*837*0002~  ← Transaction 2
    ...
    SE*45*0002~
  GE*2*1234~      ← 2 transaction sets
IEA*1*000000001~
```

### Empty vs. missing elements

```
NM1*IL*1*SMITH**A~     ← Elements: ["IL", "1", "SMITH", "", "A"]
                                                    ^^ empty first name
```

Empty string (`""`) means the element is present but has no value.
If an element is beyond the last provided element, treat it as absent/null.

### Composite element detection

Any element containing the sub-element separator (`:`) is composite:

```python
def parse_element(value: str, sub_sep: str) -> Union[str, list]:
    if sub_sep in value:
        return value.split(sub_sep)
    return value
```

Common composites:
- `SV1-01`: `HC:99213` (procedure code qualifier + CPT code)
- `CLM-05`: `11:B:1` (place of service + qualifier + frequency)
- `HI-01+`: `BK:M5416` (diagnosis qualifier + ICD-10 code)
- `CAS adjustment groups`: Always simple, but SVC-01 is composite

### The repetition separator

In 5010, the `^` character separates repeated values within a single element:

```
EB*1**1^33^35^47~
       ^^^^^^^^^ → Service type codes: [1, 33, 35, 47]
```

Parse repeated elements after splitting composites:

```python
def parse_element_full(value, sub_sep, rep_sep):
    # First check for repetition
    if rep_sep and rep_sep in value:
        return [parse_composite(v, sub_sep) for v in value.split(rep_sep)]
    return parse_composite(value, sub_sep)
```

### Segment terminator in data

Rare, but possible: if the segment terminator appears in data (e.g., free text
fields), it should be escaped or the segment terminator should be chosen to
avoid conflicts. In practice, this almost never happens with `~`.

---

## 15. Common Code Tables

### NM1 Entity Identifier Codes (NM1-01)

| Code | Entity | Context |
|------|--------|---------|
| 40 | Receiver | Loop 1000B |
| 41 | Submitter | Loop 1000A |
| 85 | Billing Provider | Loop 2010AA |
| 87 | Pay-to Provider | Loop 2010AB |
| IL | Insured/Subscriber | Loop 2010BA |
| PR | Payer | Loop 2010BB |
| QC | Patient (in 835) | Loop 2100 |
| PE | Payee (in 835) | Loop 1000B |
| X3 | UM Organization (in 278) | Loop 2000A |
| 1P | Provider (in 270/271/278) | Loop 2000B |

### NM1 Entity Type Qualifier (NM1-02)

| Code | Meaning |
|------|---------|
| 1 | Person (individual) |
| 2 | Non-Person Entity (organization) |

### NM1 Identification Code Qualifier (NM1-08)

| Code | ID Type |
|------|---------|
| MI | Member Identification Number |
| PI | Payer Identification |
| XX | NPI (National Provider Identifier) |
| 46 | ETIN (Electronic Transmitter ID) |
| EI | Employer's ID Number |
| SV | Service Provider Number |

### Place of Service Codes (CLM-05, SV1-05, UM-04)

| Code | Description |
|------|-------------|
| 11 | Office |
| 12 | Home |
| 21 | Inpatient Hospital |
| 22 | Outpatient Hospital |
| 23 | Emergency Room |
| 24 | Ambulatory Surgical Center |
| 31 | Skilled Nursing Facility |
| 49 | Independent Clinic |

### Claim Filing Indicator (SBR-09, CLP-06)

| Code | Description |
|------|-------------|
| WC | Workers' Compensation |
| MB | Medicare Part B |
| MC | Medicaid |
| BL | Blue Cross/Blue Shield |
| CI | Commercial Insurance |
| HM | HMO |

### DTP Date/Time Qualifier Codes

| Code | Meaning | Used In |
|------|---------|---------|
| 291 | Service Date (Plan) | 270 |
| 346 | Plan Begin | 271 |
| 347 | Plan End | 271 |
| 405 | Production Date | 835 |
| 431 | Statement Date | 837P |
| 472 | Service Date | 837P/835/278 |
| 232 | Claim Statement Period Start | 835 |
| 233 | Claim Statement Period End | 835 |

### DTP Date Format Codes (DTP-02)

| Code | Format | Example |
|------|--------|---------|
| D8 | Single date (YYYYMMDD) | 20260205 |
| RD8 | Date range (YYYYMMDD-YYYYMMDD) | 20260205-20260305 |

---

## Appendix: Quick Reference for Building an Importer

### Minimum viable parser checklist

1. [ ] Detect delimiters from ISA (positions 3, 82, 104, 105)
2. [ ] Split file into segments on segment terminator
3. [ ] Split each segment into elements on element separator
4. [ ] Match ISA/IEA, GS/GE, ST/SE pairs and validate control numbers
5. [ ] Route to type-specific parser based on GS01 or ST01
6. [ ] Build HL hierarchy tree for 837P/270/271/278
7. [ ] Parse composites (split on `:`) for SV1-01, CLM-05, HI-01, etc.
8. [ ] Handle repeated elements (split on `^`) for EB-03 service types
9. [ ] Handle trailing empty elements gracefully
10. [ ] Validate SE01 segment count

### Generating test data

Use the companion generator tool to create test files:

```bash
# Small file for developing your parser
python3 edi_generator.py --type 837P --claims 2 --pretty --seed 1

# Large file for load testing
python3 edi_generator.py --type 835 --claims 500 --output big_test.edi

# All types at once
python3 edi_generator.py --type all --claims 20 --output-dir ./test_data --pretty
```
