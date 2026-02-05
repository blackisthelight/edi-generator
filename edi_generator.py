#!/usr/bin/env python3
"""
EDI X12 File Generator

Generates sample EDI X12 transaction sets for testing and development purposes.
Supports common transaction types: 850 (Purchase Order), 810 (Invoice),
856 (Advance Ship Notice), and 997 (Functional Acknowledgment).

Usage:
    python edi_generator.py [options]

Examples:
    python edi_generator.py --type 850
    python edi_generator.py --type 810 --output invoice.edi
    python edi_generator.py --type 856 --items 5 --pretty
    python edi_generator.py --type 997
    python edi_generator.py --type all --output-dir ./samples
"""

import argparse
import os
import random
import string
import sys
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pad(value, length, fill=" ", align="left"):
    """Pad a string to a fixed length."""
    s = str(value)[:length]
    if align == "left":
        return s.ljust(length, fill)
    return s.rjust(length, fill)


def control_number(digits=9):
    """Generate a zero-padded random control number."""
    return str(random.randint(1, 10**digits - 1)).zfill(digits)


def date_str(dt=None, fmt="%Y%m%d"):
    """Format a datetime as an EDI date string."""
    return (dt or datetime.now()).strftime(fmt)


def time_str(dt=None, fmt="%H%M"):
    """Format a datetime as an EDI time string."""
    return (dt or datetime.now()).strftime(fmt)


# ---------------------------------------------------------------------------
# Sample data pools
# ---------------------------------------------------------------------------

COMPANY_NAMES = [
    "ACME CORP", "GLOBEX INC", "INITECH LLC", "UMBRELLA CO",
    "WAYNE ENTERPRISES", "STARK INDUSTRIES", "CYBERDYNE SYSTEMS",
    "OSCORP INDUSTRIES", "SOYLENT CORP", "MASSIVE DYNAMIC",
]

ADDRESSES = [
    ("123 MAIN ST", "NEW YORK", "NY", "10001"),
    ("456 OAK AVE", "LOS ANGELES", "CA", "90001"),
    ("789 PINE RD", "CHICAGO", "IL", "60601"),
    ("321 ELM BLVD", "HOUSTON", "TX", "77001"),
    ("654 MAPLE DR", "PHOENIX", "AZ", "85001"),
    ("987 CEDAR LN", "SEATTLE", "WA", "98101"),
    ("111 BIRCH CT", "DENVER", "CO", "80201"),
    ("222 WALNUT ST", "ATLANTA", "GA", "30301"),
]

PRODUCTS = [
    ("WIDGET-A100", "Industrial Widget Type A", 12.50, "EA"),
    ("GADGET-B200", "Electronic Gadget Model B", 45.99, "EA"),
    ("BOLT-HX-10MM", "Hex Bolt 10mm Grade 8", 0.35, "PK"),
    ("PIPE-SCH40-2", "Steel Pipe SCH40 2 inch", 28.75, "FT"),
    ("FILTER-OIL-5", "Oil Filter 5 Micron", 8.99, "EA"),
    ("CABLE-CAT6-B", "CAT6 Ethernet Cable Blue", 15.40, "EA"),
    ("BEARING-6205", "Ball Bearing 6205-2RS", 6.25, "EA"),
    ("SEAL-ORING-L", "O-Ring Seal Large", 1.10, "BG"),
    ("MOTOR-AC-1HP", "AC Motor 1HP 1750RPM", 189.00, "EA"),
    ("VALVE-GATE-3", "Gate Valve 3 inch Brass", 74.50, "EA"),
]

CARRIERS = [
    ("UPSN", "UPS GROUND"),
    ("FEDX", "FEDEX EXPRESS"),
    ("USPS", "USPS PRIORITY"),
    ("RDWY", "ROADWAY EXPRESS"),
    ("ABFS", "ABF FREIGHT"),
]

PAYMENT_TERMS = [
    ("01", "NET 30"),
    ("02", "NET 60"),
    ("05", "2% 10 NET 30"),
    ("08", "NET 15"),
    ("14", "DUE ON RECEIPT"),
]


# ---------------------------------------------------------------------------
# EDI Envelope helpers
# ---------------------------------------------------------------------------

class EDIBuilder:
    """Builds an EDI X12 document with proper enveloping."""

    def __init__(self, element_sep="*", segment_term="~", sub_element_sep=":"):
        self.element_sep = element_sep
        self.segment_term = segment_term
        self.sub_element_sep = sub_element_sep
        self.segments = []

    def add(self, segment_id, *elements):
        """Add a segment with its elements."""
        parts = [segment_id] + [str(e) for e in elements]
        self.segments.append(self.element_sep.join(parts) + self.segment_term)

    def segment_count(self):
        return len(self.segments)

    def render(self, pretty=False):
        """Render the full EDI document."""
        sep = "\n" if pretty else ""
        return sep.join(self.segments)
        if pretty:
            return "\n".join(self.segments)
        return "".join(self.segments)


def build_envelope(builder, sender_id, receiver_id, func_id_code,
                   transaction_segments, version="00401"):
    """Wrap transaction segments in ISA/GS/ST ... SE/GE/IEA envelope."""
    now = datetime.now()
    isa_control = control_number(9)
    gs_control = control_number(4)
    st_control = control_number(4).zfill(4)

    # ISA - Interchange Control Header (fixed-width elements)
    builder.add(
        "ISA",
        "00",                          # ISA01 - Auth Info Qualifier
        pad("", 10),                   # ISA02 - Auth Info
        "00",                          # ISA03 - Security Info Qualifier
        pad("", 10),                   # ISA04 - Security Info
        "ZZ",                          # ISA05 - Sender ID Qualifier
        pad(sender_id, 15),            # ISA06 - Sender ID
        "ZZ",                          # ISA07 - Receiver ID Qualifier
        pad(receiver_id, 15),          # ISA08 - Receiver ID
        date_str(now, "%y%m%d"),       # ISA09 - Date
        time_str(now),                 # ISA10 - Time
        "U",                           # ISA11 - Repetition Separator
        "00401",                       # ISA12 - Version
        isa_control,                   # ISA13 - Control Number
        "0",                           # ISA14 - Ack Requested
        "T",                           # ISA15 - Usage (T=Test, P=Production)
        builder.sub_element_sep,       # ISA16 - Sub-element Separator
    )

    # GS - Functional Group Header
    builder.add(
        "GS",
        func_id_code,                  # GS01 - Functional ID Code
        sender_id,                     # GS02 - Application Sender
        receiver_id,                   # GS03 - Application Receiver
        date_str(now),                 # GS04 - Date
        time_str(now),                 # GS05 - Time
        gs_control,                    # GS06 - Group Control Number
        "X",                           # GS07 - Responsible Agency
        "004010",                      # GS08 - Version
    )

    # ST - Transaction Set Header
    builder.add("ST", func_id_to_txn(func_id_code), st_control)

    # -- Transaction body --
    for seg_id, *elements in transaction_segments:
        builder.add(seg_id, *elements)

    # SE - Transaction Set Trailer
    # Count = all segments from ST to SE inclusive
    se_count = len(transaction_segments) + 2  # ST + body + SE
    builder.add("SE", str(se_count), st_control)

    # GE - Functional Group Trailer
    builder.add("GE", "1", gs_control)

    # IEA - Interchange Control Trailer
    builder.add("IEA", "1", isa_control)


def func_id_to_txn(func_id_code):
    """Map GS functional ID code to transaction set ID."""
    return {
        "PO": "850",
        "IN": "810",
        "SH": "856",
        "FA": "997",
    }.get(func_id_code, "850")


# ---------------------------------------------------------------------------
# Transaction generators
# ---------------------------------------------------------------------------

def generate_850(num_items=None):
    """Generate an EDI 850 Purchase Order transaction body."""
    num_items = num_items or random.randint(2, 6)
    po_number = "PO-" + "".join(random.choices(string.digits, k=7))
    po_date = datetime.now() - timedelta(days=random.randint(0, 5))
    delivery_date = po_date + timedelta(days=random.randint(14, 45))

    buyer = random.choice(COMPANY_NAMES)
    seller = random.choice([c for c in COMPANY_NAMES if c != buyer])
    ship_addr = random.choice(ADDRESSES)
    bill_addr = random.choice(ADDRESSES)
    carrier_code, carrier_name = random.choice(CARRIERS)
    terms_code, terms_desc = random.choice(PAYMENT_TERMS)

    segments = []

    # BEG - Beginning Segment for Purchase Order
    segments.append(("BEG", "00", "NE", po_number, "", date_str(po_date)))

    # CUR - Currency
    segments.append(("CUR", "BY", "USD"))

    # REF - Reference
    segments.append(("REF", "DP", "".join(random.choices(string.digits, k=4))))

    # PER - Contact
    segments.append(("PER", "BD", "PURCHASING DEPT", "TE", f"555{random.randint(1000000,9999999)}"))

    # ITD - Terms of Sale
    segments.append(("ITD", terms_code, "3", "", "", "", "", "30"))

    # DTM - Delivery Date
    segments.append(("DTM", "002", date_str(delivery_date)))

    # TD5 - Carrier Details
    segments.append(("TD5", "", "2", carrier_code, "", carrier_name))

    # N1/N3/N4 - Ship To
    segments.append(("N1", "ST", buyer, "92", "".join(random.choices(string.digits, k=10))))
    segments.append(("N3", ship_addr[0]))
    segments.append(("N4", ship_addr[1], ship_addr[2], ship_addr[3], "US"))

    # N1/N3/N4 - Bill To
    segments.append(("N1", "BT", buyer, "92", "".join(random.choices(string.digits, k=10))))
    segments.append(("N3", bill_addr[0]))
    segments.append(("N4", bill_addr[1], bill_addr[2], bill_addr[3], "US"))

    # N1 - Seller
    segments.append(("N1", "VN", seller, "92", "".join(random.choices(string.digits, k=10))))

    # PO1 - Line Items
    total_amount = 0.0
    items = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
    for i, (sku, desc, price, uom) in enumerate(items, 1):
        qty = random.randint(1, 100)
        line_total = round(qty * price, 2)
        total_amount += line_total
        segments.append(("PO1", str(i), str(qty), uom, f"{price:.2f}", "PE", "VP", sku))
        segments.append(("PID", "F", "", "", "", desc))

    # CTT - Transaction Totals
    segments.append(("CTT", str(len(items))))

    # AMT - Monetary Amount
    segments.append(("AMT", "TT", f"{total_amount:.2f}"))

    return segments, buyer, seller


def generate_810(num_items=None):
    """Generate an EDI 810 Invoice transaction body."""
    num_items = num_items or random.randint(2, 6)
    inv_number = "INV-" + "".join(random.choices(string.digits, k=7))
    inv_date = datetime.now()
    po_number = "PO-" + "".join(random.choices(string.digits, k=7))
    po_date = inv_date - timedelta(days=random.randint(10, 30))

    buyer = random.choice(COMPANY_NAMES)
    seller = random.choice([c for c in COMPANY_NAMES if c != buyer])
    addr = random.choice(ADDRESSES)
    terms_code, terms_desc = random.choice(PAYMENT_TERMS)

    segments = []

    # BIG - Beginning Segment for Invoice
    segments.append(("BIG", date_str(inv_date), inv_number, date_str(po_date), po_number))

    # REF - Reference
    segments.append(("REF", "DP", "".join(random.choices(string.digits, k=4))))

    # N1/N3/N4 - Remit To
    segments.append(("N1", "RE", seller, "92", "".join(random.choices(string.digits, k=10))))
    segments.append(("N3", addr[0]))
    segments.append(("N4", addr[1], addr[2], addr[3], "US"))

    # N1 - Buyer
    segments.append(("N1", "BY", buyer, "92", "".join(random.choices(string.digits, k=10))))

    # ITD - Terms
    segments.append(("ITD", terms_code, "3", "", "", "", "", "30"))

    # IT1 - Line Items
    total_amount = 0.0
    items = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
    for i, (sku, desc, price, uom) in enumerate(items, 1):
        qty = random.randint(1, 100)
        line_total = round(qty * price, 2)
        total_amount += line_total
        segments.append(("IT1", str(i), str(qty), uom, f"{price:.2f}", "", "VP", sku))
        segments.append(("PID", "F", "", "", "", desc))

    # TDS - Total Monetary Value Summary (in cents)
    segments.append(("TDS", str(int(total_amount * 100))))

    # CTT - Transaction Totals
    segments.append(("CTT", str(len(items))))

    return segments, seller, buyer


def generate_856(num_items=None):
    """Generate an EDI 856 Advance Ship Notice transaction body."""
    num_items = num_items or random.randint(2, 5)
    ship_date = datetime.now()
    shipment_id = "SH-" + "".join(random.choices(string.digits, k=8))
    po_number = "PO-" + "".join(random.choices(string.digits, k=7))

    shipper = random.choice(COMPANY_NAMES)
    receiver = random.choice([c for c in COMPANY_NAMES if c != shipper])
    ship_from = random.choice(ADDRESSES)
    ship_to = random.choice([a for a in ADDRESSES if a != ship_from])
    carrier_code, carrier_name = random.choice(CARRIERS)

    segments = []

    # BSN - Beginning Segment for Ship Notice
    segments.append(("BSN", "00", shipment_id, date_str(ship_date), time_str(ship_date), "0001"))

    # HL - Shipment Level
    hl_count = 1
    segments.append(("HL", str(hl_count), "", "S"))

    # TD1 - Carrier Details (Quantity and Weight)
    total_weight = round(random.uniform(10, 500), 1)
    segments.append(("TD1", "CTN25", str(num_items), "", "", "", "G", f"{total_weight}", "LB"))

    # TD5 - Carrier Details (Routing)
    segments.append(("TD5", "", "2", carrier_code, "", carrier_name))

    # TD3 - Carrier Details (Equipment)
    segments.append(("TD3", "TL", "", "".join(random.choices(string.ascii_uppercase + string.digits, k=8))))

    # REF - Reference Numbers
    tracking = "1Z" + "".join(random.choices(string.digits, k=16))
    segments.append(("REF", "BM", shipment_id))
    segments.append(("REF", "CN", tracking))

    # DTM - Ship Date
    segments.append(("DTM", "011", date_str(ship_date)))

    # N1/N3/N4 - Ship From
    segments.append(("N1", "SH", shipper, "92", "".join(random.choices(string.digits, k=10))))
    segments.append(("N3", ship_from[0]))
    segments.append(("N4", ship_from[1], ship_from[2], ship_from[3], "US"))

    # N1/N3/N4 - Ship To
    segments.append(("N1", "ST", receiver, "92", "".join(random.choices(string.digits, k=10))))
    segments.append(("N3", ship_to[0]))
    segments.append(("N4", ship_to[1], ship_to[2], ship_to[3], "US"))

    # HL - Order Level
    hl_count += 1
    segments.append(("HL", str(hl_count), "1", "O"))
    segments.append(("PRF", po_number))

    # HL - Item Levels
    items = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
    for i, (sku, desc, price, uom) in enumerate(items, 1):
        hl_count += 1
        qty = random.randint(1, 50)
        segments.append(("HL", str(hl_count), "2", "I"))
        segments.append(("LIN", str(i), "VP", sku))
        segments.append(("SN1", str(i), str(qty), uom))
        segments.append(("PID", "F", "", "", "", desc))

    # CTT - Transaction Totals
    segments.append(("CTT", str(hl_count)))

    return segments, shipper, receiver


def generate_997():
    """Generate an EDI 997 Functional Acknowledgment transaction body."""
    ack_date = datetime.now()
    orig_gs_control = control_number(4)
    orig_st_control = control_number(4).zfill(4)

    sender = random.choice(COMPANY_NAMES)
    receiver = random.choice([c for c in COMPANY_NAMES if c != sender])

    # Randomly pick a transaction type we're acknowledging
    ack_txn = random.choice(["850", "810", "856"])
    func_code = {"850": "PO", "810": "IN", "856": "SH"}[ack_txn]

    segments = []

    # AK1 - Functional Group Response Header
    segments.append(("AK1", func_code, orig_gs_control))

    # AK2 - Transaction Set Response Header
    segments.append(("AK2", ack_txn, orig_st_control))

    # AK5 - Transaction Set Response Trailer
    # A = Accepted, E = Accepted with Errors, R = Rejected
    status = random.choice(["A", "A", "A", "E"])
    segments.append(("AK5", status))

    # AK9 - Functional Group Response Trailer
    # A = Accepted, P = Partially Accepted, R = Rejected
    segments.append(("AK9", "A", "1", "1", "1"))

    return segments, sender, receiver


# ---------------------------------------------------------------------------
# Main generator dispatch
# ---------------------------------------------------------------------------

GENERATORS = {
    "850": ("PO", generate_850, "Purchase Order"),
    "810": ("IN", generate_810, "Invoice"),
    "856": ("SH", generate_856, "Advance Ship Notice"),
    "997": ("FA", generate_997, "Functional Acknowledgment"),
}


def generate_edi(txn_type, num_items=None, pretty=False):
    """Generate a complete EDI document for the given transaction type."""
    if txn_type not in GENERATORS:
        raise ValueError(f"Unsupported transaction type: {txn_type}. "
                         f"Supported: {', '.join(GENERATORS.keys())}")

    func_code, generator, description = GENERATORS[txn_type]

    if txn_type == "997":
        body_segments, sender, receiver = generator()
    else:
        body_segments, sender, receiver = generator(num_items)

    sender_id = sender.replace(" ", "")[:15]
    receiver_id = receiver.replace(" ", "")[:15]

    builder = EDIBuilder()
    build_envelope(builder, sender_id, receiver_id, func_code,
                   body_segments)

    return builder.render(pretty=pretty), description


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate sample EDI X12 files for testing and development.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported transaction types:
  850  Purchase Order
  810  Invoice
  856  Advance Ship Notice (ASN)
  997  Functional Acknowledgment
  all  Generate one of each type

Examples:
  %(prog)s --type 850
  %(prog)s --type 810 --output invoice.edi
  %(prog)s --type 856 --items 5 --pretty
  %(prog)s --type all --output-dir ./samples
        """,
    )
    parser.add_argument(
        "--type", "-t",
        choices=["850", "810", "856", "997", "all"],
        default="850",
        help="EDI transaction type to generate (default: 850)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout). Ignored when --type=all.",
    )
    parser.add_argument(
        "--output-dir", "-d",
        help="Output directory for 'all' mode (default: current directory).",
    )
    parser.add_argument(
        "--items", "-n",
        type=int,
        help="Number of line items to include (default: random 2-6).",
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Add newlines between segments for readability.",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="Random seed for reproducible output.",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.type == "all":
        output_dir = args.output_dir or "."
        os.makedirs(output_dir, exist_ok=True)
        for txn_type in GENERATORS:
            content, desc = generate_edi(txn_type, args.items, args.pretty)
            filename = f"sample_{txn_type}.edi"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
                if args.pretty:
                    f.write("\n")
            print(f"Generated {txn_type} ({desc}): {filepath}")
        return

    content, desc = generate_edi(args.type, args.items, args.pretty)

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
