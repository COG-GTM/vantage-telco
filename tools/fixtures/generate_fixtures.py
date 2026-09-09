"""Generate the shared billing fixture set for vantage-telco and meridian-telco.

Both estates bill the same customers from the same usage feed, so the inputs are
generated once, here, and written out in each system's native format:

    vantage-telco   data/seed/accounts.json, data/seed/usage.json
    meridian-telco  billing/accounts/*.rec, data/accounts.csv, data/usage.csv

Accounts are joined across the two systems on ``billing_ref`` (TN-nnnn); the
account identifiers themselves differ, as they do in the real estate.

    python tools/fixtures/generate_fixtures.py --meridian-dir ../meridian-telco
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    """Write with LF endings: the meridian parsers keep the trailing CR."""
    path.write_text(text, newline="\n")


ACCOUNT_COUNT = 200
PERIODS = ["2026-06", "2026-07"]
PROVINCES = ["BC", "AB", "ON", "QC"]

# The customers that already existed in both estates before the billing rework.
# Their identifiers are preserved so existing dashboards and tests keep working.
LEGACY_ACCOUNTS = [
    ("Beacon Manufacturing Corp", "47-2214880", "BEACON-004417", "VANTAGE-BILL-88213"),
    ("Northgate Logistics LLC", "26-8841902", "MER-011000", "VANTAGE-BILL-70000"),
    ("Cedar Point Health Systems", "31-5528117", "MER-011007", "VANTAGE-BILL-70013"),
    ("Willow Grove Retail Group", "45-9930221", "MER-011014", "VANTAGE-BILL-70026"),
    ("Stonebridge Financial", "12-7741550", "MER-011021", "VANTAGE-BILL-70039"),
    ("Kingsley Media Networks", "77-1120983", "MER-011028", "VANTAGE-BILL-70052"),
    ("Ashford Public Schools", "04-6621174", "MER-011035", "VANTAGE-BILL-70065"),
    ("Foxglove Biotech", "83-4410927", "MER-011042", "VANTAGE-BILL-70078"),
]

NAME_HEADS = [
    "Cascade",
    "Fraser",
    "Kootenay",
    "Athabasca",
    "Bow River",
    "Chinook",
    "Prairie Rose",
    "Rideau",
    "Humber",
    "Georgian Bay",
    "Trillium",
    "Laurentide",
    "Saguenay",
    "Richelieu",
    "Gaspesie",
    "Selkirk",
    "Okanagan",
    "Bonaventure",
    "Peace River",
    "Nechako",
    "Algonquin",
    "Lakeshore",
    "Saint-Laurent",
    "Beauport",
    "Sherbrooke",
    "Wapiti",
    "Redwater",
    "Coquitlam",
]
NAME_TAILS = [
    "Logistics",
    "Health Network",
    "Retail Group",
    "Manufacturing",
    "Energy Services",
    "Credit Union",
    "Media Networks",
    "School Board",
    "Biotech",
    "Transit Authority",
    "Food Distribution",
    "Engineering",
    "Mining",
    "Hospitality Group",
    "Analytics",
]
SUFFIXES = ["Inc.", "Ltd.", "Corp.", "ULC"]

STREETS = {
    "BC": [
        ("Burrard St", "Vancouver", "V6C 2G8"),
        ("Douglas St", "Victoria", "V8W 2B7"),
        ("Columbia Ave", "Kamloops", "V2C 1L2"),
        ("Lougheed Hwy", "Burnaby", "V5C 4Y2"),
    ],
    "AB": [
        ("Stephen Ave", "Calgary", "T2P 1J9"),
        ("Jasper Ave", "Edmonton", "T5J 1W8"),
        ("Gaetz Ave", "Red Deer", "T4N 4E1"),
        ("Mayor Magrath Dr", "Lethbridge", "T1K 2R1"),
    ],
    "ON": [
        ("Bay St", "Toronto", "M5J 2T3"),
        ("Elgin St", "Ottawa", "K2P 1L4"),
        ("King St W", "Kitchener", "N2G 1B3"),
        ("Ouellette Ave", "Windsor", "N9A 1C4"),
    ],
    "QC": [
        ("Rue Sainte-Catherine", "Montreal", "H3B 1A7"),
        ("Boulevard Charest", "Quebec City", "G1K 3H8"),
        ("Rue King Ouest", "Sherbrooke", "J1H 1P9"),
        ("Boulevard Talbot", "Saguenay", "G7H 4B3"),
    ],
}

PLANS = [
    ("ENT-5000", 5000, 4200.00),
    ("ENT-2500", 2500, 2400.00),
    ("ENT-1000", 1000, 1150.00),
    ("BIZ-500", 500, 640.00),
    ("BIZ-250", 250, 380.00),
]


def _account(rng: random.Random, index: int) -> dict[str, Any]:
    billing_ref = f"TN-{index + 1:04d}"
    if index < len(LEGACY_ACCOUNTS):
        legal_name, tax_id, meridian_id, vantage_id = LEGACY_ACCOUNTS[index]
    else:
        legal_name = f"{rng.choice(NAME_HEADS)} {rng.choice(NAME_TAILS)} {rng.choice(SUFFIXES)}"
        tax_id = f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}"
        meridian_id = f"MER-{11049 + (index - len(LEGACY_ACCOUNTS)) * 7:06d}"
        vantage_id = f"VANTAGE-BILL-{70091 + (index - len(LEGACY_ACCOUNTS)) * 13:05d}"

    province = PROVINCES[index % len(PROVINCES)]
    street, city, postal = rng.choice(STREETS[province])
    plan_code, included_gb, plan_fee = PLANS[index % len(PLANS)]

    # Roughly a third of the book changed plan mid-cycle; the previous plan is
    # always an adjacent tier so the proration delta is visible but not absurd.
    plan_change_day = 0
    previous_plan_fee = 0.0
    if index % 3 == 0:
        plan_change_day = rng.choice([4, 9, 12, 17, 21, 26])
        previous_plan_fee = PLANS[(index + 1) % len(PLANS)][2]

    promo_amount = 0.0
    promo_issued_on = ""
    if index % 4 in (0, 1):
        promo_amount = float(rng.choice([75, 120, 200, 350]))
        # Issued either inside the July cycle or late in June; the June issues are
        # what separate "expires at cycle end" from "expires 30 days after issue".
        promo_issued_on = str(
            date(2026, 6, 22) + timedelta(days=rng.choice([0, 2, 5, 7, 14, 20, 26]))
        )

    suspension_start_day = 0
    suspension_end_day = 0
    if index % 25 == 7:
        suspension_start_day = rng.choice([6, 11, 18])
        suspension_end_day = suspension_start_day + rng.choice([3, 6, 9])

    prior_balance = 0.0
    prior_due_date = ""
    if index % 5 in (0, 3):
        prior_balance = round(rng.uniform(180, 2600), 2)
        prior_due_date = str(date(2026, 6, 10) + timedelta(days=rng.choice([0, 4, 9, 15, 20])))

    return {
        "billing_ref": billing_ref,
        "meridian_account_id": meridian_id,
        "vantage_account_id": vantage_id,
        "legal_name": legal_name,
        "tax_id": tax_id,
        "service_address": f"{rng.randint(20, 4800)} {street}, {city}, {province} {postal}",
        "province": province,
        "plan_code": plan_code,
        "plan_monthly_fee": plan_fee,
        "included_gb": included_gb,
        "previous_plan_fee": previous_plan_fee,
        "plan_change_day": plan_change_day,
        "line_count": rng.choice([1, 2, 3, 4, 6, 8, 11, 14, 22]),
        "promo_credit_amount": promo_amount,
        "promo_issued_on": promo_issued_on,
        "suspension_start_day": suspension_start_day,
        "suspension_end_day": suspension_end_day,
        "prior_balance": prior_balance,
        "prior_due_date": prior_due_date,
        "loyalty_discount_pct": rng.choice([0.0, 3.0, 4.0, 5.0, 8.0]),
    }


def _usage(rng: random.Random, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for index, account in enumerate(accounts):
        included_mb = account["included_gb"] * 1024
        for period in PERIODS:
            if index % 6 == 2:
                # Just over the allowance: a sub-gigabyte overage, which the two
                # rating engines price very differently.
                usage_mb = included_mb + rng.randint(15, 900)
            elif index % 6 == 5:
                usage_mb = rng.randint(int(included_mb * 0.55), included_mb)
            else:
                usage_mb = int(included_mb * rng.uniform(1.05, 1.9))
            records.append(
                {
                    "billing_ref": account["billing_ref"],
                    "period": period,
                    "usage_mb": usage_mb,
                }
            )
    return records


def build_fixtures() -> dict[str, Any]:
    rng = random.Random(20260818)
    accounts = [_account(rng, index) for index in range(ACCOUNT_COUNT)]
    return {"accounts": accounts, "usage": _usage(rng, accounts)}


def write_vantage(fixtures: dict[str, Any], root: Path) -> None:
    seed_dir = root / "data" / "seed"
    accounts = [
        {
            "account_id": a["vantage_account_id"],
            "billing_ref": a["billing_ref"],
            "legal_name": a["legal_name"],
            "tax_id": a["tax_id"],
            "service_address": a["service_address"],
            "province": a["province"],
            "plan_code": a["plan_code"],
            "plan_monthly_fee": a["plan_monthly_fee"],
            "included_gb": a["included_gb"],
            "previous_plan_fee": a["previous_plan_fee"],
            "plan_change_day": a["plan_change_day"],
            "line_count": a["line_count"],
            "promo_credit_amount": a["promo_credit_amount"],
            "promo_issued_on": a["promo_issued_on"],
            "suspension_start_day": a["suspension_start_day"],
            "suspension_end_day": a["suspension_end_day"],
            "prior_balance": a["prior_balance"],
            "prior_due_date": a["prior_due_date"],
            "loyalty_discount_pct": a["loyalty_discount_pct"],
        }
        for a in fixtures["accounts"]
    ]
    by_ref = {a["billing_ref"]: a["vantage_account_id"] for a in fixtures["accounts"]}

    devices = [d["device_uuid"] for d in json.loads((seed_dir / "devices.json").read_text())]
    usage = []
    for index, record in enumerate(fixtures["usage"]):
        usage.append(
            {
                "usage_id": f"VU-{record['period']}-{index + 1:04d}",
                "account_id": by_ref[record["billing_ref"]],
                "device_uuid": devices[index % len(devices)],
                "period": record["period"],
                "usage_mb": record["usage_mb"],
            }
        )
    # Mediated usage that never found a billing account. Kept from the original
    # seed: the unbilled-usage panel and its test depend on these two records.
    for period in PERIODS:
        usage.append(
            {
                "usage_id": f"VU-{period}-0447",
                "account_id": None,
                "device_uuid": "4424bc47-f1e7-2d27-b338-24241faaa002",
                "period": period,
                "usage_mb": 118_442 if period == "2026-06" else 121_907,
            }
        )

    _write(seed_dir / "accounts.json", json.dumps(accounts, indent=2) + "\n")
    _write(seed_dir / "usage.json", json.dumps(usage, indent=2) + "\n")


REC_FIELDS = [
    ("ACCT_ID", "meridian_account_id"),
    ("BILLING_REF", "billing_ref"),
    ("CUST_NM", "legal_name"),
    ("TAX_ID", "tax_id"),
    ("SVC_ADDR", "service_address"),
    ("PROVINCE", "province"),
    ("PLAN_CD", "plan_code"),
    ("PLAN_FEE", "plan_monthly_fee"),
    ("INCLUDED_GB", "included_gb"),
    ("PREV_PLAN_FEE", "previous_plan_fee"),
    ("PLAN_CHG_DAY", "plan_change_day"),
    ("LINE_CNT", "line_count"),
    ("PROMO_AMT", "promo_credit_amount"),
    ("PROMO_DT", "promo_issued_on"),
    ("SUSP_START", "suspension_start_day"),
    ("SUSP_END", "suspension_end_day"),
    ("PRIOR_BAL", "prior_balance"),
    ("PRIOR_DUE", "prior_due_date"),
    ("LOYALTY_PCT", "loyalty_discount_pct"),
]


def write_meridian(fixtures: dict[str, Any], root: Path) -> None:
    accounts_dir = root / "billing" / "accounts"
    accounts_dir.mkdir(parents=True, exist_ok=True)
    for stale in accounts_dir.glob("*.rec"):
        stale.unlink()

    for account in fixtures["accounts"]:
        lines = [f"{key}={account[field]}" for key, field in REC_FIELDS]
        _write(accounts_dir / f"{account['meridian_account_id']}.rec", "\n".join(lines) + "\n")

    with (root / "data" / "accounts.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([key for key, _ in REC_FIELDS])
        for account in fixtures["accounts"]:
            writer.writerow([account[field] for _, field in REC_FIELDS])

    by_ref = {a["billing_ref"]: a["meridian_account_id"] for a in fixtures["accounts"]}
    with (root / "data" / "usage.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["ACCT_ID", "PERIOD", "USAGE_MB"])
        for record in fixtures["usage"]:
            writer.writerow([by_ref[record["billing_ref"]], record["period"], record["usage_mb"]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--meridian-dir",
        default=str(REPO_ROOT.parent / "meridian-telco"),
        help="path to a meridian-telco clone (default: sibling directory)",
    )
    parser.add_argument("--vantage-only", action="store_true")
    args = parser.parse_args()

    fixtures = build_fixtures()
    write_vantage(fixtures, REPO_ROOT)
    print(
        f"vantage-telco: {len(fixtures['accounts'])} accounts, "
        f"{len(fixtures['usage'])} usage records"
    )

    if args.vantage_only:
        return
    meridian_root = Path(args.meridian_dir).resolve()
    if not (meridian_root / "billing").is_dir():
        raise SystemExit(f"no meridian-telco checkout at {meridian_root}")
    write_meridian(fixtures, meridian_root)
    print(f"meridian-telco: written to {meridian_root}")


if __name__ == "__main__":
    main()
