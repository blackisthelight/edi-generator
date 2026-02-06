#!/usr/bin/env python3
"""
Healthcare EDI X12 5010 File Generator

Generates sample HIPAA-compliant EDI X12 transaction sets for testing and
development in the healthcare / workers' compensation managed care domain.

Modeled after the types of EDI files that flow between insurance payers,
managed care organizations (like One Call), and healthcare providers.

Supported transaction types:
  837P  Health Care Claim - Professional (provider -> payer/MCO)
  835   Health Care Claim Payment/Remittance Advice (payer -> provider)
  270   Eligibility Inquiry (provider/MCO -> payer)
  271   Eligibility Response (payer -> provider/MCO)
  278   Health Care Services Review - Authorization Request (provider -> payer/MCO)
  999   Implementation Acknowledgment (receiver -> sender)

Usage:
    python edi_generator.py [options]

Examples:
    python edi_generator.py --type 837P
    python edi_generator.py --type 835 --output remittance.edi --claims 5
    python edi_generator.py --type 278 --pretty
    python edi_generator.py --type all --output-dir ./samples
"""

import argparse
import os
import random
import string
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pad(value, length, fill=" "):
    """Pad a string to a fixed length (left-aligned)."""
    return str(value)[:length].ljust(length, fill)


def control_number(digits=9):
    """Generate a zero-padded random control number."""
    return str(random.randint(1, 10**digits - 1)).zfill(digits)


def date_str(dt=None, fmt="%Y%m%d"):
    return (dt or datetime.now()).strftime(fmt)


def time_str(dt=None, fmt="%H%M"):
    return (dt or datetime.now()).strftime(fmt)


def npi():
    """Generate a random 10-digit NPI (National Provider Identifier)."""
    return "1" + "".join(random.choices(string.digits, k=9))


def member_id():
    """Generate a random member/subscriber ID."""
    return "".join(random.choices(string.ascii_uppercase, k=3)) + "".join(random.choices(string.digits, k=9))


def claim_id():
    """Generate a random claim control number."""
    return "".join(random.choices(string.digits, k=12))


def tax_id():
    """Generate a random 9-digit tax ID (EIN)."""
    return "".join(random.choices(string.digits, k=9))


# ---------------------------------------------------------------------------
# Sample data pools — healthcare / workers' comp context
# ---------------------------------------------------------------------------

PAYER_NAMES = [
    ("TRAVELERS INSURANCE", "61425"),
    ("HARTFORD FINANCIAL", "36273"),
    ("LIBERTY MUTUAL GROUP", "71412"),
    ("SEDGWICK CMS", "59274"),
    ("GALLAGHER BASSETT", "23189"),
    ("ZURICH INSURANCE", "99281"),
    ("EMPLOYERS HOLDINGS", "45917"),
]

MANAGED_CARE_ORGS = [
    ("ONE CALL CARE MANAGEMENT", "ONECALL", "1234567890"),
    ("COVENTRY WC", "COVWC", "2345678901"),
    ("CORVEL CORPORATION", "CORVEL", "3456789012"),
    ("FIRST HEALTH NETWORK", "FHNET", "4567890123"),
]

PROVIDER_NAMES = [
    ("SMITH", "ROBERT", "MD"),
    ("JOHNSON", "MARIA", "DO"),
    ("WILLIAMS", "JAMES", "DC"),
    ("BROWN", "PATRICIA", "PT"),
    ("DAVIS", "MICHAEL", "OT"),
    ("GARCIA", "JENNIFER", "DPM"),
    ("MILLER", "DAVID", "MD"),
    ("WILSON", "LINDA", "PhD"),
]

FACILITY_NAMES = [
    "PREMIER ORTHOPEDIC CENTER",
    "REGIONAL REHABILITATION CLINIC",
    "ADVANCED IMAGING ASSOCIATES",
    "COASTAL PHYSICAL THERAPY",
    "METRO PAIN MANAGEMENT",
    "SUMMIT SURGICAL CENTER",
    "VALLEY SPINE INSTITUTE",
    "HARBOR OCCUPATIONAL HEALTH",
]

PATIENT_NAMES = [
    ("THOMPSON", "WILLIAM", "A", "M", "19780315"),
    ("MARTINEZ", "SARAH", "L", "F", "19850622"),
    ("ANDERSON", "JOHN", "R", "M", "19700108"),
    ("TAYLOR", "ELIZABETH", "M", "F", "19920417"),
    ("THOMAS", "RICHARD", "D", "M", "19650930"),
    ("JACKSON", "MICHELLE", "K", "F", "19880211"),
    ("WHITE", "CHRISTOPHER", "J", "M", "19750820"),
    ("HARRIS", "AMANDA", "S", "F", "19830714"),
]

ADDRESSES = [
    ("123 MAIN ST", "JACKSONVILLE", "FL", "32256"),
    ("456 OAK AVE", "DALLAS", "TX", "75201"),
    ("789 PINE RD", "COLUMBUS", "OH", "43215"),
    ("321 ELM BLVD", "TAMPA", "FL", "33602"),
    ("654 MAPLE DR", "PHOENIX", "AZ", "85004"),
    ("987 CEDAR LN", "NASHVILLE", "TN", "37203"),
    ("111 BIRCH CT", "DENVER", "CO", "80202"),
    ("222 WALNUT ST", "PORTLAND", "OR", "97201"),
]

# CPT / HCPCS codes common in workers' comp / managed care
PROCEDURE_CODES = [
    ("99213", "Office visit - established, moderate", 95.00),
    ("99214", "Office visit - established, high", 145.00),
    ("99203", "Office visit - new, moderate", 165.00),
    ("97110", "Therapeutic exercises", 42.00),
    ("97140", "Manual therapy techniques", 45.00),
    ("97530", "Therapeutic activities", 40.00),
    ("97112", "Neuromuscular re-education", 44.00),
    ("72148", "MRI lumbar spine w/o contrast", 475.00),
    ("72141", "MRI cervical spine w/o contrast", 450.00),
    ("73721", "MRI lower extremity joint w/o", 425.00),
    ("20610", "Arthrocentesis major joint", 125.00),
    ("64483", "Epidural injection lumbar/sacral", 350.00),
    ("27447", "Total knee replacement", 2850.00),
    ("29881", "Knee arthroscopy/meniscectomy", 1200.00),
    ("98940", "Chiropractic manipulation 1-2 regions", 55.00),
    ("98941", "Chiropractic manipulation 3-4 regions", 65.00),
    ("97035", "Ultrasound therapy", 25.00),
    ("97010", "Hot/cold pack application", 15.00),
]

ICD10_CODES = [
    ("M5416", "Radiculopathy, lumbar region"),
    ("M5412", "Radiculopathy, cervical region"),
    ("S8350XA", "Sprain of knee, unspecified, initial"),
    ("M7911", "Myalgia, right shoulder"),
    ("S4300XA", "Dislocation of shoulder joint, initial"),
    ("M5136", "Intervertebral disc degeneration, lumbar"),
    ("S93401A", "Sprain of ankle, initial encounter"),
    ("G8929", "Other chronic pain"),
    ("M75110", "Rotator cuff tear, right shoulder"),
    ("S62009A", "Fracture of navicular bone of wrist, initial"),
    ("M7010", "Bursitis of knee"),
    ("S83511A", "Sprain of ACL of right knee, initial"),
]

PLACE_OF_SERVICE = [
    ("11", "Office"),
    ("22", "Outpatient Hospital"),
    ("24", "Ambulatory Surgical Center"),
    ("49", "Independent Clinic"),
]

CLAIM_ADJ_REASON_CODES = [
    ("1", "Deductible"),
    ("2", "Coinsurance"),
    ("3", "Copayment"),
    ("45", "Charges exceed fee schedule/maximum allowable"),
    ("97", "Payment adjusted - authorized return"),
    ("A2", "Contractual adjustment"),
    ("CO", "Contractual obligations"),
]

AUTH_SERVICE_TYPES = [
    ("PT", "Physical Therapy", "3"),
    ("OT", "Occupational Therapy", "3"),
    ("MR", "MRI", "1"),
    ("SC", "Surgical Consultation", "1"),
    ("PM", "Pain Management", "3"),
    ("DC", "Chiropractic", "3"),
    ("DI", "Diagnostic Imaging", "1"),
    ("SG", "Surgery", "1"),
]


# ---------------------------------------------------------------------------
# One Call Care Management — Line of Business (LOB) profiles
#
# Each LOB constrains the CPT codes, provider types, facility names,
# ICD-10 codes, and auth service types to those consistent with that
# line of business.  Use --lob <name> to activate.
#
# LOBs based on One Call's service lines:
#   PT        Physical Therapy (incl. aqua, hand therapy, work hardening)
#   OT        Occupational Therapy
#   DC        Chiropractic
#   DX        Diagnostics (MRI, CT, X-ray, EMG/NCS, ultrasound)
#   DME       Durable Medical Equipment
#   HH        Home Health / Complex Care
#   DENTAL    Dental
#   TRANSPORT Transportation
#   LANGUAGE  Language / Interpreter Services
# ---------------------------------------------------------------------------

LOB_PROFILES = {
    "PT": {
        "name": "Physical Therapy",
        "procedure_codes": [
            ("97110", "Therapeutic exercises", 42.00),
            ("97140", "Manual therapy techniques", 45.00),
            ("97530", "Therapeutic activities", 40.00),
            ("97112", "Neuromuscular re-education", 44.00),
            ("97035", "Ultrasound therapy", 25.00),
            ("97010", "Hot/cold pack application", 15.00),
            ("97150", "Group therapeutic procedures", 30.00),
            ("97116", "Gait training therapy", 38.00),
            ("97542", "Wheelchair management training", 42.00),
            ("97760", "Orthotic management and training", 48.00),
            ("97164", "PT re-evaluation", 85.00),
            ("97161", "PT evaluation low complexity", 95.00),
            ("97162", "PT evaluation moderate complexity", 115.00),
            ("97163", "PT evaluation high complexity", 135.00),
            ("97113", "Aquatic therapy", 48.00),
            ("97542", "Wheelchair management", 42.00),
            ("97750", "Physical performance test", 55.00),
            ("97799", "Physical therapy service", 50.00),
        ],
        "provider_names": [
            ("BROWN", "PATRICIA", "PT"),
            ("CHEN", "DAVID", "PT"),
            ("PATEL", "ANITA", "DPT"),
            ("OCONNOR", "SEAN", "PT"),
            ("RODRIGUEZ", "CARMEN", "DPT"),
            ("LARSEN", "ERIK", "PT"),
        ],
        "facility_names": [
            "COASTAL PHYSICAL THERAPY",
            "PEAK PERFORMANCE REHABILITATION",
            "PROGRESSIVE PT AND SPORTS REHAB",
            "AQUATIC THERAPY CENTER",
            "HAND AND UPPER EXTREMITY CLINIC",
            "WORK HARDENING AND CONDITIONING CTR",
            "TOTAL BODY REHABILITATION",
            "PINNACLE PHYSICAL THERAPY",
        ],
        "icd10_codes": [
            ("M5416", "Radiculopathy, lumbar region"),
            ("M5412", "Radiculopathy, cervical region"),
            ("S8350XA", "Sprain of knee, unspecified, initial"),
            ("M7911", "Myalgia, right shoulder"),
            ("S93401A", "Sprain of ankle, initial encounter"),
            ("M75110", "Rotator cuff tear, right shoulder"),
            ("M7010", "Bursitis of knee"),
            ("S83511A", "Sprain of ACL of right knee, initial"),
            ("M5136", "Intervertebral disc degeneration, lumbar"),
            ("S46011A", "Strain of rotator cuff, right shoulder, initial"),
            ("M79641", "Pain in right hand"),
            ("S62009A", "Fracture of navicular bone of wrist, initial"),
        ],
        "auth_service_types": [
            ("PT", "Physical Therapy", "3"),
        ],
        "place_of_service": [
            ("11", "Office"),
            ("49", "Independent Clinic"),
        ],
    },

    "OT": {
        "name": "Occupational Therapy",
        "procedure_codes": [
            ("97530", "Therapeutic activities", 40.00),
            ("97110", "Therapeutic exercises", 42.00),
            ("97140", "Manual therapy techniques", 45.00),
            ("97535", "Self-care/home management training", 46.00),
            ("97537", "Community/work reintegration", 48.00),
            ("97542", "Wheelchair management training", 42.00),
            ("97760", "Orthotic management and training", 48.00),
            ("97167", "OT re-evaluation", 85.00),
            ("97165", "OT evaluation low complexity", 95.00),
            ("97166", "OT evaluation moderate complexity", 115.00),
            ("97750", "Physical performance test/FCE", 55.00),
            ("29125", "Forearm splint application", 65.00),
            ("29130", "Finger splint application", 45.00),
            ("97112", "Neuromuscular re-education", 44.00),
        ],
        "provider_names": [
            ("DAVIS", "MICHAEL", "OT"),
            ("NAKAMURA", "KENJI", "OTR"),
            ("BROOKS", "LISA", "OT"),
            ("HOFFMAN", "ANNA", "OTR/L"),
            ("GARCIA", "CARLOS", "OT"),
        ],
        "facility_names": [
            "HARBOR OCCUPATIONAL HEALTH",
            "FUNCTIONAL RESTORATION CENTER",
            "HAND AND UPPER EXTREMITY CLINIC",
            "WORK HARDENING AND CONDITIONING CTR",
            "OCCUPATIONAL REHAB SPECIALISTS",
            "CERTIFIED HAND THERAPY CENTER",
        ],
        "icd10_codes": [
            ("S62009A", "Fracture of navicular bone of wrist, initial"),
            ("S66011A", "Strain of flexor tendon of right thumb, initial"),
            ("M79641", "Pain in right hand"),
            ("S4300XA", "Dislocation of shoulder joint, initial"),
            ("M7911", "Myalgia, right shoulder"),
            ("G5600", "Carpal tunnel syndrome, unspecified"),
            ("S63011A", "Subluxation of distal radioulnar joint, initial"),
            ("M75110", "Rotator cuff tear, right shoulder"),
            ("M7010", "Bursitis of knee"),
        ],
        "auth_service_types": [
            ("OT", "Occupational Therapy", "3"),
        ],
        "place_of_service": [
            ("11", "Office"),
            ("49", "Independent Clinic"),
        ],
    },

    "DC": {
        "name": "Chiropractic",
        "procedure_codes": [
            ("98940", "Chiropractic manipulation 1-2 regions", 55.00),
            ("98941", "Chiropractic manipulation 3-4 regions", 65.00),
            ("98942", "Chiropractic manipulation 5 regions", 75.00),
            ("97140", "Manual therapy techniques", 45.00),
            ("97110", "Therapeutic exercises", 42.00),
            ("97010", "Hot/cold pack application", 15.00),
            ("97035", "Ultrasound therapy", 25.00),
            ("97012", "Mechanical traction therapy", 30.00),
            ("97014", "Electrical stimulation unattended", 20.00),
            ("97032", "Electrical stimulation manual", 35.00),
            ("97112", "Neuromuscular re-education", 44.00),
        ],
        "provider_names": [
            ("WILLIAMS", "JAMES", "DC"),
            ("PETERSON", "MARK", "DC"),
            ("CHANG", "LISA", "DC"),
            ("MURPHY", "BRIAN", "DC"),
            ("FOSTER", "DIANE", "DC"),
        ],
        "facility_names": [
            "VALLEY SPINE INSTITUTE",
            "ADVANCED CHIROPRACTIC CENTER",
            "SPINAL CARE AND REHABILITATION",
            "TOTAL WELLNESS CHIROPRACTIC",
            "APEX SPINE AND JOINT CLINIC",
        ],
        "icd10_codes": [
            ("M5416", "Radiculopathy, lumbar region"),
            ("M5412", "Radiculopathy, cervical region"),
            ("M5136", "Intervertebral disc degeneration, lumbar"),
            ("M5432", "Cervicalgia"),
            ("M5442", "Lumbago with sciatica, left side"),
            ("M545", "Low back pain"),
            ("M9901", "Segmental and somatic dysfunction of cervical"),
            ("M9903", "Segmental and somatic dysfunction of lumbar"),
            ("G8929", "Other chronic pain"),
        ],
        "auth_service_types": [
            ("DC", "Chiropractic", "3"),
        ],
        "place_of_service": [
            ("11", "Office"),
        ],
    },

    "DX": {
        "name": "Diagnostics",
        "procedure_codes": [
            ("72148", "MRI lumbar spine w/o contrast", 475.00),
            ("72141", "MRI cervical spine w/o contrast", 450.00),
            ("73721", "MRI lower extremity joint w/o", 425.00),
            ("73221", "MRI upper extremity joint w/o", 415.00),
            ("72149", "MRI lumbar spine w/ contrast", 575.00),
            ("73720", "MRI lower extremity w/o then w/", 650.00),
            ("72131", "CT lumbar spine w/o contrast", 325.00),
            ("72125", "CT cervical spine w/o contrast", 310.00),
            ("73700", "CT lower extremity w/o contrast", 295.00),
            ("73200", "CT upper extremity w/o contrast", 285.00),
            ("73030", "X-ray shoulder 2+ views", 55.00),
            ("73560", "X-ray knee 1-2 views", 45.00),
            ("73110", "X-ray wrist 3+ views", 50.00),
            ("72100", "X-ray lumbar spine 2-3 views", 65.00),
            ("76882", "Ultrasound extremity, limited", 125.00),
            ("76881", "Ultrasound extremity, complete", 175.00),
            ("95907", "EMG nerve conduction 1-2 studies", 185.00),
            ("95908", "EMG nerve conduction 3-4 studies", 250.00),
            ("95909", "EMG nerve conduction 5-6 studies", 315.00),
            ("95886", "Needle EMG each extremity", 195.00),
            ("95885", "Needle EMG limited study", 145.00),
        ],
        "provider_names": [
            ("MILLER", "DAVID", "MD"),
            ("KIM", "SUSAN", "MD"),
            ("RAMIREZ", "JORGE", "MD"),
            ("WALSH", "KATHLEEN", "DO"),
            ("SINGH", "RAJESH", "MD"),
        ],
        "facility_names": [
            "ADVANCED IMAGING ASSOCIATES",
            "PREMIER DIAGNOSTIC CENTER",
            "REGIONAL MRI AND CT CENTER",
            "OPEN MRI OF JACKSONVILLE",
            "NEURODIAGNOSTIC ASSOCIATES",
            "RADIOLOGY PARTNERS WC",
            "OUTPATIENT IMAGING CENTER",
        ],
        "icd10_codes": [
            ("M5416", "Radiculopathy, lumbar region"),
            ("M5412", "Radiculopathy, cervical region"),
            ("M5136", "Intervertebral disc degeneration, lumbar"),
            ("M75110", "Rotator cuff tear, right shoulder"),
            ("S83511A", "Sprain of ACL of right knee, initial"),
            ("S8350XA", "Sprain of knee, unspecified, initial"),
            ("G5600", "Carpal tunnel syndrome, unspecified"),
            ("M7010", "Bursitis of knee"),
            ("S4300XA", "Dislocation of shoulder joint, initial"),
            ("M7911", "Myalgia, right shoulder"),
            ("G8929", "Other chronic pain"),
        ],
        "auth_service_types": [
            ("MR", "MRI", "1"),
            ("DI", "Diagnostic Imaging", "1"),
        ],
        "place_of_service": [
            ("22", "Outpatient Hospital"),
            ("49", "Independent Clinic"),
        ],
    },

    "DME": {
        "name": "Durable Medical Equipment",
        "procedure_codes": [
            ("E0112", "Crutches, underarm, wood, pair", 45.00),
            ("E0114", "Crutches, underarm, adjustable, pair", 55.00),
            ("E0130", "Walker, rigid, adjustable", 85.00),
            ("E0143", "Walker, folding, wheeled", 125.00),
            ("E0601", "CPAP device", 450.00),
            ("E0720", "TENS unit 2-lead", 120.00),
            ("E0730", "TENS unit 4-lead", 150.00),
            ("E0935", "Continuous passive motion device", 275.00),
            ("E1390", "Oxygen concentrator", 325.00),
            ("E0185", "Gel mattress overlay", 175.00),
            ("L0631", "Lumbar support, prefabricated", 85.00),
            ("L1832", "Knee orthosis, adjustable", 245.00),
            ("L3808", "Wrist hand orthosis, rigid", 165.00),
            ("L3916", "Ankle foot orthosis, rigid", 295.00),
            ("L3960", "Shoulder elbow orthosis", 385.00),
            ("A4556", "Electrodes for TENS per pair", 12.00),
            ("A4558", "TENS unit supplies, 2-lead, per month", 35.00),
            ("E0193", "Powered air flotation mattress", 475.00),
            ("K0001", "Standard wheelchair", 350.00),
            ("K0004", "High strength lightweight wheelchair", 850.00),
        ],
        "provider_names": [
            ("ORTHOTECH", "SUPPLY", "DME"),
            ("MEDLINE", "SERVICES", "DME"),
            ("NATIONAL", "SEATING", "DME"),
            ("PROSTHETIC", "SOLUTIONS", "CP"),
        ],
        "facility_names": [
            "NATIONAL DME PROVIDERS",
            "MEDICAL EQUIPMENT SPECIALISTS",
            "REHAB TECHNOLOGY SOLUTIONS",
            "PROSTHETIC AND ORTHOTIC CENTER",
            "HOME MEDICAL SUPPLY CO",
            "ADAPTIVE EQUIPMENT SERVICES",
        ],
        "icd10_codes": [
            ("S8350XA", "Sprain of knee, unspecified, initial"),
            ("M5416", "Radiculopathy, lumbar region"),
            ("S62009A", "Fracture of navicular bone of wrist, initial"),
            ("S93401A", "Sprain of ankle, initial encounter"),
            ("M75110", "Rotator cuff tear, right shoulder"),
            ("S4300XA", "Dislocation of shoulder joint, initial"),
            ("G8929", "Other chronic pain"),
            ("M7010", "Bursitis of knee"),
        ],
        "auth_service_types": [
            ("DM", "Durable Medical Equipment", "1"),
        ],
        "place_of_service": [
            ("12", "Home"),
            ("49", "Independent Clinic"),
        ],
    },

    "HH": {
        "name": "Home Health / Complex Care",
        "procedure_codes": [
            ("99341", "Home visit new patient, low", 95.00),
            ("99342", "Home visit new patient, moderate", 145.00),
            ("99347", "Home visit established, low", 75.00),
            ("99348", "Home visit established, moderate", 115.00),
            ("99349", "Home visit established, high", 155.00),
            ("99504", "Home visit nursing care, complex", 125.00),
            ("99507", "Home visit for wound care", 110.00),
            ("97110", "Therapeutic exercises (home PT)", 42.00),
            ("97530", "Therapeutic activities (home OT)", 40.00),
            ("S9123", "Nursing care in home per hour, RN", 85.00),
            ("S9124", "Nursing care in home per hour, LPN", 55.00),
            ("T1030", "Nursing care in home, per diem, RN", 450.00),
            ("T1031", "Nursing care in home, per diem, LPN", 300.00),
            ("G0299", "Skilled nursing services, home health", 65.00),
            ("G0300", "Skilled nursing services, maintenance", 55.00),
        ],
        "provider_names": [
            ("MARTINEZ", "ELENA", "RN"),
            ("THOMPSON", "GRACE", "RN"),
            ("WRIGHT", "JAMES", "LPN"),
            ("BELL", "SANDRA", "RN"),
            ("COLE", "PATRICK", "PT"),
        ],
        "facility_names": [
            "HOME CARE NURSING SERVICES",
            "COMPLEX CARE SOLUTIONS",
            "VISITING HEALTH PROFESSIONALS",
            "POST ACUTE CARE NETWORK",
            "HOME REHABILITATION SERVICES",
            "CATASTROPHIC CARE MANAGEMENT",
        ],
        "icd10_codes": [
            ("S7200XA", "Fracture of head of femur, initial"),
            ("G8929", "Other chronic pain"),
            ("S1200XA", "Fracture of first cervical vertebra, initial"),
            ("S3210XA", "Fracture of body of sternum, initial"),
            ("T8430XA", "Infection following procedure, initial"),
            ("S0600XA", "Concussion w/o loss of consciousness, initial"),
            ("L97519", "Non-pressure chronic ulcer of lower leg"),
            ("M5416", "Radiculopathy, lumbar region"),
        ],
        "auth_service_types": [
            ("HH", "Home Health", "3"),
            ("CC", "Complex Care", "3"),
        ],
        "place_of_service": [
            ("12", "Home"),
        ],
    },

    "DENTAL": {
        "name": "Dental",
        "procedure_codes": [
            ("D0120", "Periodic oral evaluation", 45.00),
            ("D0140", "Limited oral evaluation, problem focused", 65.00),
            ("D0150", "Comprehensive oral evaluation", 85.00),
            ("D0220", "Intraoral periapical first radiograph", 25.00),
            ("D0230", "Intraoral periapical each additional", 18.00),
            ("D0274", "Bitewing radiographs four images", 55.00),
            ("D0330", "Panoramic radiograph", 95.00),
            ("D2140", "Amalgam restoration one surface", 125.00),
            ("D2150", "Amalgam restoration two surfaces", 155.00),
            ("D2330", "Resin composite one surface anterior", 145.00),
            ("D2740", "Crown porcelain/ceramic substrate", 850.00),
            ("D2750", "Crown porcelain fused to metal", 795.00),
            ("D3310", "Root canal anterior tooth", 475.00),
            ("D3320", "Root canal premolar tooth", 575.00),
            ("D3330", "Root canal molar tooth", 725.00),
            ("D7140", "Extraction erupted tooth", 135.00),
            ("D7210", "Surgical extraction", 225.00),
            ("D7240", "Surgical extraction impacted tooth", 325.00),
        ],
        "provider_names": [
            ("PARK", "ANDREW", "DDS"),
            ("SHAW", "MELISSA", "DMD"),
            ("RIVERA", "DANIEL", "DDS"),
            ("TRAN", "LINDA", "DMD"),
            ("WOOD", "CHARLES", "DDS"),
        ],
        "facility_names": [
            "ONE CALL DENTAL NETWORK",
            "WORKERS COMP DENTAL CENTER",
            "OCCUPATIONAL DENTAL ASSOCIATES",
            "PREMIER DENTAL CARE WC",
            "INDUSTRIAL DENTAL CLINIC",
        ],
        "icd10_codes": [
            ("S0250XA", "Fracture of tooth, initial encounter"),
            ("K0889", "Other specified disorders of teeth"),
            ("K0461", "Dental caries on pit and fissure surface"),
            ("K0501", "Dental caries on root surface"),
            ("S0351XA", "Fracture of alveolar process of mandible, initial"),
            ("K0830", "Enamel erosion, unspecified"),
            ("K0400", "Dental caries, enamel limited"),
        ],
        "auth_service_types": [
            ("DN", "Dental", "1"),
        ],
        "place_of_service": [
            ("11", "Office"),
        ],
    },

    "TRANSPORT": {
        "name": "Transportation",
        "procedure_codes": [
            ("A0100", "Non-emergency ambulance transport", 350.00),
            ("A0120", "Non-emergency wheelchair van", 125.00),
            ("A0130", "Non-emergency ambulance, wheelchair", 175.00),
            ("A0160", "Non-emergency stretcher transport", 225.00),
            ("A0170", "Transport ancillary, parking fees", 15.00),
            ("A0180", "Transport ancillary, tolls", 10.00),
            ("A0190", "Transport ancillary, per mile", 2.50),
            ("A0200", "Transport ancillary, waiting time", 35.00),
            ("T2003", "Non-emergency transport, encounter/trip", 65.00),
            ("T2005", "Non-emergency transport, per mile", 2.00),
            ("S0215", "Non-emergency transport, mileage per mile", 1.75),
        ],
        "provider_names": [
            ("TRANSMED", "SERVICES", "EMT"),
            ("PREMIER", "TRANSPORT", "EMT"),
            ("METRO", "MEDICAL", "EMT"),
            ("NATIONAL", "TRANSPORT", "EMT"),
        ],
        "facility_names": [
            "MEDICAL TRANSPORT SERVICES",
            "NON EMERGENCY TRANSPORT LLC",
            "WORKERS COMP TRANSPORTATION",
            "METRO MEDICAL TRANSPORT",
            "ACCESSIBLE TRANSIT SERVICES",
        ],
        "icd10_codes": [
            ("Z0289", "Encounter for other administrative examinations"),
            ("M5416", "Radiculopathy, lumbar region"),
            ("G8929", "Other chronic pain"),
            ("S8350XA", "Sprain of knee, unspecified, initial"),
            ("M75110", "Rotator cuff tear, right shoulder"),
        ],
        "auth_service_types": [
            ("TR", "Transportation", "1"),
        ],
        "place_of_service": [
            ("99", "Other Place of Service"),
        ],
    },

    "LANGUAGE": {
        "name": "Language / Interpreter Services",
        "procedure_codes": [
            ("T1013", "Interpreter services, per 15 minutes", 25.00),
            ("T1012", "Interpreter services, per encounter", 85.00),
            ("S9542", "Home infusion, sign language", 95.00),
            ("T2048", "Behavioral health, translation", 45.00),
        ],
        "provider_names": [
            ("LINGUISTIC", "SERVICES", "CI"),
            ("CERTIFIED", "INTERPRETERS", "CI"),
            ("MULTILINGUAL", "GROUP", "CI"),
        ],
        "facility_names": [
            "LANGUAGE LINE SOLUTIONS",
            "CERTIFIED INTERPRETER SERVICES",
            "WORKERS COMP LANGUAGE SERVICES",
            "MULTILINGUAL COMMUNICATION SVCS",
        ],
        "icd10_codes": [
            ("Z0289", "Encounter for other administrative examinations"),
            ("M5416", "Radiculopathy, lumbar region"),
            ("G8929", "Other chronic pain"),
        ],
        "auth_service_types": [
            ("LS", "Language Services", "1"),
        ],
        "place_of_service": [
            ("11", "Office"),
            ("22", "Outpatient Hospital"),
        ],
    },
}

# Active data pools — overridden when --lob is specified
active_procedure_codes = PROCEDURE_CODES
active_provider_names = PROVIDER_NAMES
active_facility_names = FACILITY_NAMES
active_icd10_codes = ICD10_CODES
active_auth_service_types = AUTH_SERVICE_TYPES
active_place_of_service = PLACE_OF_SERVICE


def apply_lob(lob_name):
    """Override the active data pools with LOB-specific data."""
    global active_procedure_codes, active_provider_names, active_facility_names
    global active_icd10_codes, active_auth_service_types, active_place_of_service

    if lob_name is None:
        return

    lob_key = lob_name.upper()
    if lob_key not in LOB_PROFILES:
        valid = ", ".join(sorted(LOB_PROFILES.keys()))
        raise ValueError(f"Unknown LOB: {lob_name}. Valid options: {valid}")

    profile = LOB_PROFILES[lob_key]
    active_procedure_codes = profile["procedure_codes"]
    active_provider_names = profile["provider_names"]
    active_facility_names = profile["facility_names"]
    active_icd10_codes = profile["icd10_codes"]
    active_auth_service_types = profile["auth_service_types"]
    active_place_of_service = profile["place_of_service"]


# ---------------------------------------------------------------------------
# EDI Builder
# ---------------------------------------------------------------------------

class EDIBuilder:
    """Builds an EDI X12 document with proper enveloping."""

    def __init__(self, element_sep="*", segment_term="~", sub_element_sep=":"):
        self.element_sep = element_sep
        self.segment_term = segment_term
        self.sub_element_sep = sub_element_sep
        self.segments = []

    def add(self, segment_id, *elements):
        parts = [segment_id] + [str(e) for e in elements]
        self.segments.append(self.element_sep.join(parts) + self.segment_term)

    def segment_count(self):
        return len(self.segments)

    def render(self, pretty=False):
        sep = "\n" if pretty else ""
        return sep.join(self.segments)


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------

# Map: transaction type -> (GS functional ID code, ST transaction set ID, GS version)
TXN_META = {
    "837P": ("HC", "837", "005010X222A1"),
    "835":  ("HP", "835", "005010X221A1"),
    "270":  ("HS", "270", "005010X279A1"),
    "271":  ("HB", "271", "005010X279A1"),
    "278":  ("HI", "278", "005010X217"),
    "999":  ("FA", "999", "005010X231A1"),
}


def build_envelope(builder, sender_id, receiver_id, txn_type,
                   transaction_segments):
    """Wrap transaction segments in ISA/GS/ST ... SE/GE/IEA envelope."""
    now = datetime.now()
    isa_control = control_number(9)
    gs_control = control_number(4)
    st_control = control_number(4).zfill(4)
    func_code, st_id, gs_version = TXN_META[txn_type]

    # ISA - Interchange Control Header
    builder.add(
        "ISA",
        "00", pad("", 10),             # Auth info
        "00", pad("", 10),             # Security info
        "ZZ", pad(sender_id, 15),      # Sender
        "ZZ", pad(receiver_id, 15),    # Receiver
        date_str(now, "%y%m%d"),       # Date
        time_str(now),                 # Time
        "^",                           # Repetition separator (5010)
        "00501",                       # ISA version (5010)
        isa_control,                   # Control number
        "0",                           # Ack requested
        "T",                           # Usage indicator (T=Test)
        builder.sub_element_sep,       # Sub-element separator
    )

    # GS - Functional Group Header
    builder.add(
        "GS",
        func_code, sender_id, receiver_id,
        date_str(now), time_str(now),
        gs_control, "X", gs_version,
    )

    # ST - Transaction Set Header
    builder.add("ST", st_id, st_control, gs_version)

    # -- Transaction body --
    for seg_id, *elements in transaction_segments:
        builder.add(seg_id, *elements)

    # SE - Transaction Set Trailer (ST + body segments + SE)
    se_count = len(transaction_segments) + 2
    builder.add("SE", str(se_count), st_control)

    # GE - Functional Group Trailer
    builder.add("GE", "1", gs_control)

    # IEA - Interchange Control Trailer
    builder.add("IEA", "1", isa_control)


# ---------------------------------------------------------------------------
# 837P — Health Care Claim (Professional)
# ---------------------------------------------------------------------------

def generate_837p(num_claims=None):
    """Generate a professional health care claim (837P)."""
    num_claims = num_claims or random.randint(3, 10)

    submitter_name = random.choice(active_facility_names)
    payer_name, payer_id = random.choice(PAYER_NAMES)
    mco = random.choice(MANAGED_CARE_ORGS)

    segments = []

    # BHT - Beginning of Hierarchical Transaction
    segments.append(("BHT", "0019", "00",
                     "".join(random.choices(string.digits, k=8)),
                     date_str(), time_str(), "CH"))

    # -- Loop 1000A: Submitter
    segments.append(("NM1", "41", "2", submitter_name, "", "", "", "", "46",
                     "".join(random.choices(string.ascii_uppercase + string.digits, k=6))))
    segments.append(("PER", "IC", "EDI DEPARTMENT", "TE",
                     f"555{random.randint(1000000,9999999)}"))

    # -- Loop 1000B: Receiver (payer / MCO)
    segments.append(("NM1", "40", "2", payer_name, "", "", "", "", "46", payer_id))

    # -- Billing Provider HL
    billing_provider = random.choice(active_provider_names)
    billing_npi = npi()
    billing_tin = tax_id()
    billing_addr = random.choice(ADDRESSES)

    hl_id = 1
    segments.append(("HL", str(hl_id), "", "20", "1"))
    segments.append(("PRV", "BI", "PXC", "207X00000X"))  # Taxonomy code

    # NM1 - Billing Provider Name
    segments.append(("NM1", "85", "1",
                     billing_provider[0], billing_provider[1], billing_provider[2],
                     "", "", "XX", billing_npi))
    segments.append(("N3", billing_addr[0]))
    segments.append(("N4", billing_addr[1], billing_addr[2], billing_addr[3]))
    segments.append(("REF", "EI", billing_tin))

    for claim_num in range(num_claims):
        patient = random.choice(PATIENT_NAMES)
        patient_member_id = member_id()
        patient_addr = random.choice(ADDRESSES)
        pos_code, pos_name = random.choice(active_place_of_service)

        # -- Subscriber HL
        hl_id += 1
        sub_hl = hl_id
        segments.append(("HL", str(hl_id), "1", "22", "0"))
        segments.append(("SBR", "P", "", "", "", "", "", "", "", "WC"))

        # NM1 - Subscriber Name
        segments.append(("NM1", "IL", "1",
                         patient[0], patient[1], patient[2],
                         "", "", "MI", patient_member_id))
        segments.append(("N3", patient_addr[0]))
        segments.append(("N4", patient_addr[1], patient_addr[2], patient_addr[3]))
        segments.append(("DMG", "D8", patient[4], patient[3]))

        # NM1 - Payer Name
        segments.append(("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id))

        # -- Claim Loop (2300)
        claim_ctrl = claim_id()
        diag_codes = random.sample(active_icd10_codes,
                                   min(random.randint(1, 3), len(active_icd10_codes)))
        service_date = datetime.now() - timedelta(days=random.randint(1, 30))
        total_charge = 0.0

        # Select procedures
        num_svc_lines = min(random.randint(1, 4), len(active_procedure_codes))
        procedures = random.sample(active_procedure_codes, num_svc_lines)

        for cpt, desc, price in procedures:
            total_charge += price

        # CLM - Claim Information
        segments.append(("CLM", claim_ctrl, f"{total_charge:.2f}", "",
                         "", f"{pos_code}:B:1", "Y", "A", "Y", "I"))

        # DTP - Date of Service (statement dates)
        segments.append(("DTP", "431", "D8", date_str(service_date)))

        # REF - Claim Identifiers
        segments.append(("REF", "D9", claim_ctrl))

        # Workers' comp specific - REF for WC claim number
        wc_claim = "WC" + "".join(random.choices(string.digits, k=10))
        segments.append(("REF", "Y4", wc_claim))

        # HI - Diagnosis Codes
        hi_elements = ["BK:" + diag_codes[0][0]]
        for code, desc in diag_codes[1:]:
            hi_elements.append("BF:" + code)
        segments.append(("HI", *hi_elements))

        # -- Service Line Loop (2400)
        for svc_idx, (cpt, desc, price) in enumerate(procedures, 1):
            qty = 1
            segments.append(("LX", str(svc_idx)))
            # SV1 - Professional Service
            segments.append(("SV1", f"HC:{cpt}", f"{price:.2f}", "UN",
                             str(qty), pos_code, "", str(svc_idx)))
            # DTP - Date of Service
            segments.append(("DTP", "472", "D8", date_str(service_date)))

    sender_id = submitter_name.replace(" ", "")[:15]
    receiver_id = payer_name.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# 835 — Health Care Claim Payment / Remittance Advice
# ---------------------------------------------------------------------------

def generate_835(num_claims=None):
    """Generate a remittance advice (835)."""
    num_claims = num_claims or random.randint(5, 15)

    payer_name, payer_id = random.choice(PAYER_NAMES)
    payer_addr = random.choice(ADDRESSES)

    segments = []

    # BPR - Financial Information
    total_payment = 0.0  # will be updated after claims
    check_num = "".join(random.choices(string.digits, k=8))
    pay_date = datetime.now()

    # placeholder — we'll compute actual total and build BPR first in list
    bpr_idx = len(segments)
    segments.append(None)  # placeholder

    # TRN - Reassociation Trace Number
    segments.append(("TRN", "1", check_num, "1" + payer_id))

    # DTM - Production Date
    segments.append(("DTM", "405", date_str(pay_date)))

    # -- Loop 1000A: Payer Identification
    segments.append(("N1", "PR", payer_name))
    segments.append(("N3", payer_addr[0]))
    segments.append(("N4", payer_addr[1], payer_addr[2], payer_addr[3]))
    segments.append(("REF", "2U", payer_id))
    segments.append(("PER", "BL", "CLAIMS DEPT", "TE",
                     f"800{random.randint(1000000,9999999)}"))

    # -- Loop 1000B: Payee (Provider)
    payee_facility = random.choice(active_facility_names)
    payee_npi = npi()
    payee_addr = random.choice(ADDRESSES)
    segments.append(("N1", "PE", payee_facility, "XX", payee_npi))
    segments.append(("N3", payee_addr[0]))
    segments.append(("N4", payee_addr[1], payee_addr[2], payee_addr[3]))
    segments.append(("REF", "TJ", tax_id()))

    # -- Claims (Loop 2100/2110)
    for _ in range(num_claims):
        patient = random.choice(PATIENT_NAMES)
        clm_ctrl = claim_id()
        num_lines = min(random.randint(1, 3), len(active_procedure_codes))
        procedures = random.sample(active_procedure_codes, num_lines)
        service_date = pay_date - timedelta(days=random.randint(15, 60))

        # Compute charges and payments
        total_charged = sum(p[2] for p in procedures)
        allowed = round(total_charged * random.uniform(0.65, 0.90), 2)
        adjustment = round(total_charged - allowed, 2)
        claim_payment = allowed

        total_payment += claim_payment

        # CLP - Claim Payment Information
        # Status: 1=Processed as Primary, 2=Processed as Secondary
        segments.append(("CLP", clm_ctrl, "1", f"{total_charged:.2f}",
                         f"{claim_payment:.2f}", "", "WC",
                         "".join(random.choices(string.digits, k=14)), "11"))

        # CAS - Claim Adjustment (contractual obligation)
        segments.append(("CAS", "CO", "45", f"{adjustment:.2f}"))

        # NM1 - Patient Name
        segments.append(("NM1", "QC", "1", patient[0], patient[1], patient[2],
                         "", "", "MI", member_id()))

        # DTM - Statement dates
        segments.append(("DTM", "232", date_str(service_date)))
        segments.append(("DTM", "233",
                         date_str(service_date + timedelta(days=random.randint(0, 5)))))

        # -- SVC lines (Loop 2110)
        for cpt, desc, charge in procedures:
            paid = round(charge * (claim_payment / total_charged), 2)
            line_adj = round(charge - paid, 2)
            segments.append(("SVC", f"HC:{cpt}", f"{charge:.2f}",
                             f"{paid:.2f}", "", "1"))
            segments.append(("DTM", "472", date_str(service_date)))
            if line_adj > 0:
                segments.append(("CAS", "CO", "45", f"{line_adj:.2f}"))
            segments.append(("AMT", "B6", f"{paid:.2f}"))

    # PLB - Provider Level Balance (optional adjustment)
    plb_adj = round(random.uniform(-5.0, 0), 2)
    if plb_adj != 0:
        segments.append(("PLB", payee_npi, date_str(pay_date),
                         "CV:CP", f"{plb_adj:.2f}"))
        total_payment += plb_adj

    # Now fill in BPR
    segments[bpr_idx] = ("BPR", "C", f"{total_payment:.2f}", "C", "ACH", "CTX",
                         "01", "999999992", "DA", "123456",
                         "1" + payer_id, "", "01", "999988880", "DA",
                         check_num, date_str(pay_date))

    sender_id = payer_name.replace(" ", "")[:15]
    receiver_id = payee_facility.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# 270 — Eligibility Inquiry
# ---------------------------------------------------------------------------

def generate_270(num_claims=None):
    """Generate eligibility inquiries (270) for multiple subscribers."""
    num_subscribers = num_claims or random.randint(3, 10)

    payer_name, payer_id = random.choice(PAYER_NAMES)
    facility = random.choice(active_facility_names)
    provider_npi = npi()

    segments = []
    hl_id = 0

    # BHT - Beginning of Hierarchical Transaction
    segments.append(("BHT", "0022", "13",
                     "".join(random.choices(string.digits, k=8)),
                     date_str(), time_str()))

    # HL - Information Source (Payer)
    hl_id += 1
    payer_hl = hl_id
    segments.append(("HL", str(hl_id), "", "20", "1"))
    segments.append(("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id))

    # HL - Information Receiver (Provider)
    hl_id += 1
    provider_hl = hl_id
    segments.append(("HL", str(hl_id), str(payer_hl), "21", "1"))
    segments.append(("NM1", "1P", "2", facility, "", "", "", "", "XX", provider_npi))
    segments.append(("REF", "EI", tax_id()))

    # Service type codes to inquire about
    service_type_pool = [
        "30",   # Health Benefit Plan Coverage
        "1",    # Medical Care
        "33",   # Chiropractic
        "35",   # Dental Care
        "47",   # Hospital
        "86",   # Emergency Services
        "88",   # Pharmacy
        "98",   # Professional (Physician) Visit - Office
        "AL",   # Vision (Optometry)
        "MH",   # Mental Health
        "UC",   # Urgent Care
        "AJ",   # Alcoholism
        "AK",   # Drug Addiction
        "A6",   # Psychiatric
    ]

    # Multiple subscriber inquiries
    for _ in range(num_subscribers):
        patient = random.choice(PATIENT_NAMES)
        hl_id += 1

        segments.append(("HL", str(hl_id), str(provider_hl), "22", "0"))
        trace_num = "".join(random.choices(string.digits, k=12))
        segments.append(("TRN", "1", trace_num, "9" + payer_id))
        segments.append(("NM1", "IL", "1", patient[0], patient[1], patient[2],
                         "", "", "MI", member_id()))
        segments.append(("DMG", "D8", patient[4]))
        svc_date = datetime.now() - timedelta(days=random.randint(0, 14))
        segments.append(("DTP", "291", "D8", date_str(svc_date)))

        # Inquire about 1-4 service types per subscriber
        num_eq = random.randint(1, 4)
        for svc_code in random.sample(service_type_pool, num_eq):
            segments.append(("EQ", svc_code))

    sender_id = facility.replace(" ", "")[:15]
    receiver_id = payer_name.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# 271 — Eligibility Response
# ---------------------------------------------------------------------------

def generate_271(num_claims=None):
    """Generate eligibility responses (271) for multiple subscribers."""
    num_subscribers = num_claims or random.randint(3, 10)

    payer_name, payer_id = random.choice(PAYER_NAMES)
    facility = random.choice(active_facility_names)
    provider_npi = npi()

    plan_names = [
        "WC PREFERRED PLAN", "WORKERS COMP STANDARD",
        "WC MANAGED CARE GOLD", "EMPLOYERS WC PLAN A",
        "WC COMPREHENSIVE", "WC SELECT NETWORK",
    ]

    # Benefit detail templates - service types and their typical benefit info
    benefit_details = [
        # (service_type_code, description, info_type, amount_qualifier, amount)
        ("1",  "Medical Care",      "B", "27", None),   # copay varies
        ("33", "Chiropractic",      "B", "27", None),
        ("35", "Dental Care",       "B", "27", None),
        ("47", "Hospital",          "B", "29", None),   # percentage
        ("86", "Emergency",         "B", "27", None),
        ("88", "Pharmacy",          "B", "27", None),
        ("98", "Physician Visit",   "B", "27", None),
        ("AL", "Vision",            "B", "27", None),
        ("MH", "Mental Health",     "B", "27", None),
        ("UC", "Urgent Care",       "B", "27", None),
        ("A4", "Psychiatric",       "B", "27", None),
        ("A6", "Psychotherapy",     "B", "27", None),
        ("AJ", "Alcoholism",        "F", "",   None),   # deductible
        ("AK", "Drug Addiction",    "F", "",   None),
        ("PT", "Physical Therapy",  "B", "27", None),
        ("OT", "Occupational Therapy", "B", "27", None),
    ]

    segments = []
    hl_id = 0

    # BHT
    segments.append(("BHT", "0022", "11",
                     "".join(random.choices(string.digits, k=8)),
                     date_str(), time_str()))

    # HL - Information Source (Payer)
    hl_id += 1
    payer_hl = hl_id
    segments.append(("HL", str(hl_id), "", "20", "1"))
    segments.append(("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id))

    # HL - Information Receiver (Provider)
    hl_id += 1
    provider_hl = hl_id
    segments.append(("HL", str(hl_id), str(payer_hl), "21", "1"))
    segments.append(("NM1", "1P", "2", facility, "", "", "", "", "XX", provider_npi))

    for _ in range(num_subscribers):
        patient = random.choice(PATIENT_NAMES)
        patient_addr = random.choice(ADDRESSES)
        pat_member = member_id()
        plan_name = random.choice(plan_names)

        hl_id += 1
        segments.append(("HL", str(hl_id), str(provider_hl), "22", "0"))
        trace_num = "".join(random.choices(string.digits, k=12))
        segments.append(("TRN", "2", trace_num, "9" + payer_id))

        # NM1 - Subscriber
        segments.append(("NM1", "IL", "1", patient[0], patient[1], patient[2],
                         "", "", "MI", pat_member))
        segments.append(("N3", patient_addr[0]))
        segments.append(("N4", patient_addr[1], patient_addr[2], patient_addr[3]))
        segments.append(("DMG", "D8", patient[4], patient[3]))

        # INS - Subscriber Relationship
        segments.append(("INS", "Y", "18", "", "", "A"))

        # DTP - Plan dates
        eff_date = datetime.now() - timedelta(days=random.randint(30, 730))
        segments.append(("DTP", "346", "D8", date_str(eff_date)))

        # Randomly decide if subscriber is active or inactive
        is_active = random.random() < 0.85  # 85% active

        if is_active:
            # EB - Active coverage
            segments.append(("EB", "1", "", "30", "", plan_name))

            # EB - Individual benefits for several service types
            num_benefits = random.randint(4, 10)
            selected_benefits = random.sample(benefit_details, num_benefits)
            all_svc_codes = "^".join(b[0] for b in selected_benefits)

            # EB - Covered services list
            segments.append(("EB", "1", "", all_svc_codes))

            for svc_code, svc_desc, info_type, amt_qual, _ in selected_benefits:
                copay = random.choice([10, 15, 20, 25, 30, 35, 40, 50])
                if info_type == "B":  # Co-Payment
                    segments.append(("EB", "B", "IND", svc_code,
                                     "HM", plan_name, amt_qual, str(copay),
                                     "", "", "", "", "Y"))
                elif info_type == "F":  # Limitations
                    segments.append(("EB", "F", "IND", svc_code,
                                     "HM", plan_name))

                # Add per-visit/per-year limits for therapy types
                if svc_code in ("PT", "OT", "33"):
                    max_visits = random.choice([12, 20, 24, 30, 36, 52, 60])
                    segments.append(("EB", "F", "IND", svc_code,
                                     "HM", plan_name, "27", "",
                                     "", str(max_visits), "23"))

            # EB - Out-of-pocket maximum
            oop_max = random.choice([2000, 3000, 4000, 5000, 6000])
            segments.append(("EB", "G", "IND", "30", "HM", plan_name,
                             "29", str(oop_max)))

            # EB - Deductible
            deductible = random.choice([0, 250, 500, 750, 1000])
            if deductible > 0:
                segments.append(("EB", "C", "IND", "30", "HM", plan_name,
                                 "29", str(deductible)))
        else:
            # EB - Inactive coverage
            segments.append(("EB", "6", "", "30", "", plan_name))
            term_date = datetime.now() - timedelta(days=random.randint(1, 180))
            segments.append(("DTP", "347", "D8", date_str(term_date)))

    sender_id = payer_name.replace(" ", "")[:15]
    receiver_id = facility.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# 278 — Health Care Services Review (Authorization Request)
# ---------------------------------------------------------------------------

def generate_278(num_claims=None):
    """Generate authorization requests (278) for multiple patients."""
    num_requests = num_claims or random.randint(3, 8)

    payer_name, payer_id = random.choice(PAYER_NAMES)
    mco_name, mco_code, mco_npi = random.choice(MANAGED_CARE_ORGS)
    facility = random.choice(active_facility_names)

    # Review types: HS=Health Services, SC=Specialty Care, AR=Admission Review
    review_types = ["HS", "SC", "AR"]
    # Certification types: I=Initial, R=Renewal/Recertification, E=Extension
    cert_types = ["I", "I", "I", "R", "E"]

    segments = []
    hl_id = 0

    # BHT - Beginning of Hierarchical Transaction
    segments.append(("BHT", "0007", "13",
                     "".join(random.choices(string.digits, k=10)),
                     date_str(), time_str()))

    # HL - Utilization Management Organization (Payer/MCO)
    hl_id += 1
    mco_hl = hl_id
    segments.append(("HL", str(hl_id), "", "20", "1"))
    segments.append(("NM1", "X3", "2", mco_name, "", "", "", "", "46", mco_code))

    for _ in range(num_requests):
        patient = random.choice(PATIENT_NAMES)
        provider = random.choice(active_provider_names)
        provider_npi_val = npi()
        addr = random.choice(ADDRESSES)
        svc_type_code, svc_type_name, default_qty = random.choice(active_auth_service_types)

        # HL - Requester (Provider) — each request may come from a different provider
        hl_id += 1
        req_hl = hl_id
        segments.append(("HL", str(hl_id), str(mco_hl), "21", "1"))
        segments.append(("NM1", "1P", "1", provider[0], provider[1], provider[2],
                         "", "", "XX", provider_npi_val))
        segments.append(("REF", "EI", tax_id()))
        segments.append(("N3", addr[0]))
        segments.append(("N4", addr[1], addr[2], addr[3]))
        segments.append(("PER", "IC", f"{provider[1]} {provider[0]}", "TE",
                         f"555{random.randint(1000000,9999999)}"))

        # HL - Subscriber
        hl_id += 1
        sub_hl = hl_id
        pat_member = member_id()
        patient_addr = random.choice(ADDRESSES)
        segments.append(("HL", str(hl_id), str(req_hl), "22", "1"))
        segments.append(("NM1", "IL", "1", patient[0], patient[1], patient[2],
                         "", "", "MI", pat_member))
        segments.append(("N3", patient_addr[0]))
        segments.append(("N4", patient_addr[1], patient_addr[2], patient_addr[3]))
        segments.append(("DMG", "D8", patient[4], patient[3]))

        # Payer
        segments.append(("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id))

        # HL - Patient Event
        hl_id += 1
        segments.append(("HL", str(hl_id), str(sub_hl), "EV", "0"))

        # UM - Health Care Services Review Information
        review_type = random.choice(review_types)
        cert_type = random.choice(cert_types)
        pos_code = random.choice(active_place_of_service)[0]
        segments.append(("UM", review_type, cert_type, "", pos_code))

        # HI - Diagnosis (1-3 codes)
        diag_codes = random.sample(active_icd10_codes,
                                   min(random.randint(1, 3), len(active_icd10_codes)))
        hi_elements = ["BK:" + diag_codes[0][0]]
        for code, desc in diag_codes[1:]:
            hi_elements.append("BF:" + code)
        segments.append(("HI", *hi_elements))

        # HSD - Requested visits/units
        num_visits = random.randint(4, 36)
        req_start = datetime.now() + timedelta(days=random.randint(1, 14))
        req_end = req_start + timedelta(days=random.randint(30, 120))
        segments.append(("HSD", "VS", str(num_visits), "DA",
                         str((req_end - req_start).days), "7"))

        # DTP - Certification effective date range
        segments.append(("DTP", "472", "RD8",
                         date_str(req_start) + "-" + date_str(req_end)))

        # REF - Previous authorization number (for renewals/extensions)
        if cert_type in ("R", "E"):
            prev_auth = "AUTH" + "".join(random.choices(string.digits, k=8))
            segments.append(("REF", "BB", prev_auth))

        # SV1 - Service lines (1-3 procedures per request)
        num_svc = min(random.randint(1, 3), len(active_procedure_codes))
        procedures = random.sample(active_procedure_codes, num_svc)
        for proc_cpt, proc_desc, proc_price in procedures:
            qty = random.randint(1, num_visits)
            segments.append(("SV1", f"HC:{proc_cpt}", f"{proc_price:.2f}",
                             "UN", str(qty)))

    sender_id = facility.replace(" ", "")[:15]
    receiver_id = mco_name.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# 999 — Implementation Acknowledgment
# ---------------------------------------------------------------------------

def generate_999(num_claims=None):
    """Generate implementation acknowledgments (999) for multiple transaction sets."""
    num_txns = num_claims or random.randint(5, 15)

    sender = random.choice(PAYER_NAMES)
    receiver_facility = random.choice(active_facility_names)
    orig_gs_control = control_number(4)

    # Acknowledge a random healthcare transaction type
    ack_txn = random.choice(["837", "835", "270", "278"])
    func_code = {"837": "HC", "835": "HP", "270": "HS", "278": "HI"}[ack_txn]
    version_map = {
        "837": "005010X222A1", "835": "005010X221A1",
        "270": "005010X279A1", "278": "005010X217",
    }
    gs_version = version_map[ack_txn]

    # Error codes for rejected segments (IK3/IK4)
    seg_error_codes = [
        ("1", "Unrecognized segment ID"),
        ("2", "Unexpected segment"),
        ("3", "Mandatory segment missing"),
        ("5", "Segment exceeds maximum use"),
        ("8", "Segment has data element errors"),
    ]
    elem_error_codes = [
        ("1", "Mandatory data element missing"),
        ("2", "Conditional required data element missing"),
        ("4", "Data element too short"),
        ("5", "Data element too long"),
        ("6", "Invalid character in data element"),
        ("7", "Invalid code value"),
    ]

    segments = []

    # AK1 - Functional Group Response Header
    segments.append(("AK1", func_code, orig_gs_control, gs_version))

    accepted = 0
    rejected = 0

    for i in range(num_txns):
        st_control = control_number(4).zfill(4)

        # AK2 - Transaction Set Response Header
        segments.append(("AK2", ack_txn, st_control, gs_version))

        # Randomly decide status: ~70% accepted, ~15% accepted w/ errors, ~15% rejected
        roll = random.random()
        if roll < 0.70:
            status = "A"  # Accepted
            accepted += 1
        elif roll < 0.85:
            status = "E"  # Accepted with Errors
            accepted += 1
            # Add 1-2 segment error notes
            for _ in range(random.randint(1, 2)):
                seg_pos = random.randint(3, 25)
                seg_id = random.choice(["NM1", "CLM", "SV1", "DTP", "REF",
                                        "SBR", "DMG", "HI", "HL", "CLP"])
                err_code, err_desc = random.choice(seg_error_codes)
                segments.append(("IK3", seg_id, str(seg_pos), "", err_code))
                # IK4 - element-level error detail
                elem_pos = random.randint(1, 10)
                e_code, e_desc = random.choice(elem_error_codes)
                segments.append(("IK4", str(elem_pos), "", "", e_code))
        else:
            status = "R"  # Rejected
            rejected += 1
            # Add 2-4 error notes for rejected transactions
            for _ in range(random.randint(2, 4)):
                seg_pos = random.randint(3, 30)
                seg_id = random.choice(["NM1", "CLM", "SV1", "DTP", "REF",
                                        "SBR", "DMG", "HI", "HL", "CLP",
                                        "N3", "N4", "PER", "BHT"])
                err_code, err_desc = random.choice(seg_error_codes)
                segments.append(("IK3", seg_id, str(seg_pos), "", err_code))
                elem_pos = random.randint(1, 12)
                e_code, e_desc = random.choice(elem_error_codes)
                segments.append(("IK4", str(elem_pos), "", "", e_code))

        # IK5 - Transaction Set Response Trailer
        segments.append(("IK5", status))

    # AK9 - Functional Group Response Trailer
    total = accepted + rejected
    group_status = "A" if rejected == 0 else ("P" if accepted > 0 else "R")
    segments.append(("AK9", group_status, str(total), str(total), str(accepted)))

    sender_id = sender[0].replace(" ", "")[:15]
    receiver_id = receiver_facility.replace(" ", "")[:15]
    return segments, sender_id, receiver_id


# ---------------------------------------------------------------------------
# Generator dispatch
# ---------------------------------------------------------------------------

GENERATORS = {
    "837P": (generate_837p, "Health Care Claim - Professional"),
    "835":  (generate_835,  "Health Care Claim Payment/Remittance Advice"),
    "270":  (generate_270,  "Eligibility Inquiry"),
    "271":  (generate_271,  "Eligibility Response"),
    "278":  (generate_278,  "Health Care Services Review (Auth Request)"),
    "999":  (generate_999,  "Implementation Acknowledgment"),
}


def generate_edi(txn_type, num_claims=None, pretty=False):
    """Generate a complete EDI document for the given transaction type."""
    if txn_type not in GENERATORS:
        raise ValueError(f"Unsupported transaction type: {txn_type}. "
                         f"Supported: {', '.join(GENERATORS.keys())}")

    generator, description = GENERATORS[txn_type]
    body_segments, sender_id, receiver_id = generator(num_claims)

    builder = EDIBuilder()
    build_envelope(builder, sender_id, receiver_id, txn_type, body_segments)

    return builder.render(pretty=pretty), description


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    all_types = list(GENERATORS.keys())
    choices = all_types + ["all"]

    lob_choices = sorted(LOB_PROFILES.keys())

    parser = argparse.ArgumentParser(
        description="Generate sample healthcare EDI X12 5010 files for testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported transaction types:
  837P  Health Care Claim - Professional
  835   Claim Payment / Remittance Advice
  270   Eligibility Inquiry
  271   Eligibility Response
  278   Health Care Services Review (Authorization Request)
  999   Implementation Acknowledgment
  all   Generate one of each type

Lines of business (--lob):
  PT        Physical Therapy
  OT        Occupational Therapy
  DC        Chiropractic
  DX        Diagnostics (MRI, CT, X-ray, EMG/NCS)
  DME       Durable Medical Equipment
  HH        Home Health / Complex Care
  DENTAL    Dental
  TRANSPORT Transportation
  LANGUAGE  Language / Interpreter Services

  When --lob is specified, CPT codes, providers, facilities, diagnoses,
  and auth service types are constrained to that line of business.
  Based on One Call Care Management's service lines.

Context:
  These are the EDI transaction types that flow between insurance payers,
  managed care organizations (e.g. One Call), and healthcare providers in
  workers' compensation and healthcare claim processing.

Examples:
  %(prog)s --type 837P
  %(prog)s --type 835 --output remittance.edi --claims 5
  %(prog)s --type 278 --pretty
  %(prog)s --type 278 --lob PT --claims 10 --pretty
  %(prog)s --type all --output-dir ./samples
  %(prog)s --type all --lob DX --output-dir ./dx_samples
        """,
    )
    parser.add_argument(
        "--type", "-t", choices=choices, default="837P",
        help="EDI transaction type to generate (default: 837P)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout). Ignored with --type=all.",
    )
    parser.add_argument(
        "--output-dir", "-d",
        help="Output directory for 'all' mode (default: current directory).",
    )
    parser.add_argument(
        "--claims", "-n", type=int,
        help="Number of claims/items to include (default: random).",
    )
    parser.add_argument(
        "--pretty", "-p", action="store_true",
        help="Add newlines between segments for readability.",
    )
    parser.add_argument(
        "--seed", "-s", type=int,
        help="Random seed for reproducible output.",
    )
    parser.add_argument(
        "--lob", "-l",
        choices=lob_choices, type=str.upper,
        help="Limit data to a One Call line of business (e.g. PT, DX, DME).",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    apply_lob(args.lob)

    if args.type == "all":
        output_dir = args.output_dir or "."
        os.makedirs(output_dir, exist_ok=True)
        for txn_type in GENERATORS:
            content, desc = generate_edi(txn_type, args.claims, args.pretty)
            filename = f"sample_{txn_type}.edi"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
                if args.pretty:
                    f.write("\n")
            print(f"Generated {txn_type} ({desc}): {filepath}")
        return

    content, desc = generate_edi(args.type, args.claims, args.pretty)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(content)
            if args.pretty:
                f.write("\n")
        print(f"Generated {args.type} ({desc}): {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()
