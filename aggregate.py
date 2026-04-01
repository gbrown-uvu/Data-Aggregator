"""
Aggregates eBay sales data by machine/year and generates a profit report CSV.
"""

import sqlite3
import re
import json
import csv
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

DB_FILE = "ebay_sales.db"
STOP_WORDS_FILE = "stop_words.json"

TAG_PATTERN = re.compile(r"\b([A-Z0-9]{1,8}\.?\d*[A-Z]?\d*)\s*$", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def load_stop_words() -> set[str]:
    path = Path(STOP_WORDS_FILE)
    if not path.exists():
        print(f"{STOP_WORDS_FILE} not found — using default list")
        defaults = {
                        "ENGINE", "MOTOR", "BOTTOM END", "TOP END", "CRANK", "CRANKSHAFT", "CYLINDER",
            "PISTON", "HEAD", "CARB", "CARBURETOR", "CDI", "ECU", "STATOR", "FLYWHEEL",
            "CLUTCH", "TRANSMISSION", "DRIVE SHAFT", "PROP SHAFT", "DIFFERENTIAL", "AXLE",
            "FENDER", "HOOD", "PLASTIC", "BUMPER", "GRILLE", "SKID PLATE", "FOOTWELL",
            "SEAT", "TANK", "RACK", "AIRBOX", "INTAKE", "EXHAUST", "RADIATOR",
            "A ARM", "CONTROL ARM", "SHOCK", "STRUT", "TIE ROD", "BALL JOINT", "SPINDLE",
            "KNUCKLE", "STEERING", "HANDLEBAR", "THROTTLE", "BRAKE", "CALIPER", "HUB",
            "WHEEL", "RIM", "LIGHT", "HEADLIGHT", "TAILLIGHT", "GAUGE", "SWITCH", "CABLE",
            "WIRE", "HARNESS", "BATTERY", "STARTER", "WINCH", "FRAME", "SWINGARM",
            "AIR", "REAR", "BACK", "FRONT", "GAS", "FUEL", "OIL", "COOLANT", "PUMP",
            "FILTER", "HAND", "MAIN", "SPEED", "NEGATIVE", "POSITIVE", "RIGHT", "LEFT",
            "SHIFTER", "SIDE", "DRIVE", "CENTRIFUGAL", "STARTING", "LOWER", "UPPER", "COMPLETE",
            "THUMB", "BOTTOM", "TOP", "SINGLE", "INNER", "OUTER", "CAM", "CHAIN", "HOSE",
            "LINE", "MASTER", "DASH", "DISPLAY", "RECTIFIER", "VOLTAGE", "REGULATOR",
            "SECONDARY", "2ND", "CHOKE", "PARK", "IGNITION", "CENTER", "REVERSE", "KICKSTAND", 
            "OUTPUT", "ROCKER", "KICKSTART", "BELT", "TRACK", "IDLER", "GEAR"
        }
        return defaults

    with open(path, encoding="utf-8") as f:
        return set(word.upper() for word in json.load(f))


def extract_tag(title: str) -> str:
    if not title:
        return "NO_TAG"
    upper = title.upper()
    if any(x in upper for x in ["RIM", "ROW ", " X ", "X21", "X18"]):
        return "RIM_IGNORED"
    m = TAG_PATTERN.search(title)
    return m.group(1).upper() if m and not m.group(1).isdigit() else "NO_TAG"


def extract_year(title: str) -> str:
    m = YEAR_PATTERN.search(title)
    return m.group(0) if m else "Unknown"


def extract_machine_name(title: str, tag: str, stop_words: set[str]) -> str:
    clean = re.sub(rf"\s*{re.escape(tag)}$", "", title, flags=re.IGNORECASE).strip()
    clean = re.sub(r"\b(19|20)\d{2}(?:-\d{2,4})?\b", "", clean)  # remove years & ranges
    words = clean.split()

    for i, word in enumerate(words):
        base = word.upper().rstrip("S")
        if base in stop_words or word.replace("-", "") == "AARM":
            words = words[:i]
            break

    name = " ".join(words).strip()
    name = re.sub(r"\s+4X4$", " 4x4", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+2X4$", " 2x4", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(EFI|FI|LE|ES|AUTO)$", "", name, flags=re.IGNORECASE)
    return name or "Unknown"


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def main(parent=None):
    stop_words = load_stop_words()

    if not Path(DB_FILE).exists():
        print(f"{DB_FILE} not found — run 'Update Info' first")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales")
    sales = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not sales:
        print("No sales data found.")
        return

    # ── Step 1: Find canonical machine name per tag ──
    tag_to_names = defaultdict(list)
    rim_ignored = no_tag = 0

    for sale in sales:
        tag = extract_tag(sale.get("title", ""))
        if tag == "RIM_IGNORED":
            rim_ignored += 1
            continue
        if tag == "NO_TAG":
            no_tag += 1
            continue
        name = extract_machine_name(sale.get("title", ""), tag, stop_words)
        tag_to_names[tag].append(name)

    tag_to_best_name = {}
    for tag, names in tag_to_names.items():
        best = Counter(names).most_common(1)[0][0]
        if best == "Unknown" and len(names) > 1:
            best = next(n for n in names if n != "Unknown")
        tag_to_best_name[tag] = best

    # ── Step 2: Aggregate by (machine, year) ──
    groups = defaultdict(lambda: {
        "machine": "", "year": "", "tags": set(),
        "items_sold": 0, "quantity": 0,
        "revenue": 0.0, "fees": 0.0,
        "days_to_sell": [], "earliest_start": None
    })

    for sale in sales:
        tag = extract_tag(sale.get("title", ""))
        if tag not in tag_to_best_name:
            continue

        machine = tag_to_best_name[tag]
        year = extract_year(sale.get("title", ""))
        key = (machine, year)

        g = groups[key]
        if not g["machine"]:
            g["machine"] = machine
            g["year"] = year

        g["tags"].add(tag)
        g["items_sold"] += 1
        g["quantity"] += sale.get("quantity", 1)
        g["revenue"] += sale.get("sale_price_total", 0) or 0
        g["fees"] += sale.get("final_value_fee", 0) or 0

        start = parse_date(sale.get("listing_start_date"))
        sold = parse_date(sale.get("sold_date"))
        if start and sold and sold >= start:
            days = (sold - start).days
            g["days_to_sell"].append(days)
            if not g["earliest_start"] or start < g["earliest_start"]:
                g["earliest_start"] = start

    print(f"Ignored: {rim_ignored} rims, {no_tag} untagged items")

    # ── Build report rows ──
    rows = []
    for g in groups.values():
        profit = round(g["revenue"] - g["fees"], 2)
        sold_str = (f"{g['quantity']} ({g['items_sold']}×)"
                    if g["quantity"] != g["items_sold"] else str(g["quantity"]))

        avg_days = (
            "1" if g["days_to_sell"] and sum(g["days_to_sell"]) / len(g["days_to_sell"]) < 1
            else round(sum(g["days_to_sell"]) / len(g["days_to_sell"]), 1)
            if g["days_to_sell"] else "—"
        )

        rows.append({
            "Machine Name": g["machine"],
            "Year": g["year"],
            "Tags": ", ".join(sorted(g["tags"])),
            "Tag Count": len(g["tags"]),
            "Avg Days to Sell": avg_days,
            "Sold": sold_str,
            "Revenue": round(g["revenue"], 2),
            "eBay Fees": round(g["fees"], 2),
            "Total Profit": profit,
        })

    rows.sort(key=lambda x: x["Total Profit"], reverse=True)

    # ── Save CSV ──
    fieldnames = [
        "Machine Name", "Year", "Tags", "Tag Count", "Avg Days to Sell",
        "Sold", "Revenue", "eBay Fees", "Total Profit"
    ]

    default_name = f"ebay_machine_report_{datetime.now():%Y%m%d}.csv"
    file_path = filedialog.asksaveasfilename(
        parent=parent,
        title="Save Report As",
        initialdir=str(Path.home() / "Desktop"),
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:          # This catches Cancel (returns "")
        print("Save cancelled.")
        return False           # ← Tell GUI user cancelled

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Report saved: {file_path}")
    if rows:
        top = rows[0]
        print(f"Top performer → {top['Machine Name']} {top['Year']} | ${top['Total Profit']:,}")

    return True


if __name__ == "__main__":
    main()