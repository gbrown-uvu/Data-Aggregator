"""
Fetches sold transaction data from eBay API and stores it in SQLite database.
Uses 30-day chunks to stay within API limits.
"""

import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ebaysdk.trading import Connection as Trading

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

ENTRIES_PER_PAGE = 200
DB_FILE = "ebay_sales.db"
DAYS_BACK = 90
CHUNK_DAYS = 30


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def sale_exists(cursor, item_id: str, sold_date: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sales WHERE item_id = ? AND sold_date = ?",
        (item_id, sold_date)
    )
    return cursor.fetchone() is not None


def insert_sale(cursor, sale: dict) -> None:
    cursor.execute("""
        INSERT OR IGNORE INTO sales 
        (item_id, sold_date, title, listing_start_date, quantity, sale_price_total, final_value_fee)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        sale["item_id"],
        sale["sold_date"],
        sale["title"],
        sale["listing_start_date"],
        sale["quantity"],
        sale["sale_price_total"],
        sale["final_value_fee"]
    ))


def main():
    if not Path(DB_FILE).exists():
        print(f"Database not found: {DB_FILE}")
        print("Please run create_database.py first!")
        return

    api = Trading(config_file="ebay.yaml", domain="api.ebay.com", siteid="0")

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=DAYS_BACK)

    print(f"Fetching sales from {start_date.date()} → {end_date.date()} "
          f"(in {CHUNK_DAYS}-day chunks)")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sales")
    existing_count = cursor.fetchone()[0]
    print(f"Loaded {existing_count:,} existing records")

    current = start_date
    new_sales = 0

    while current < end_date:
        chunk_start = current
        chunk_end = min(current + timedelta(days=CHUNK_DAYS), end_date)

        print(f"\n--- Chunk: {chunk_start.date()} → {chunk_end.date()} ---")

        page = 1
        while True:
            try:
                response = api.execute("GetSellerTransactions", {
                    "ModTimeFrom": chunk_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "ModTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "IncludeFinalValueFee": "true",
                    "Pagination": {
                        "EntriesPerPage": ENTRIES_PER_PAGE,
                        "PageNumber": page
                    }
                })

                data = response.dict()
                txns = data.get("TransactionArray", {}).get("Transaction", [])
                if not txns:
                    print("No more transactions in this chunk")
                    break

                if not isinstance(txns, list):
                    txns = [txns]

                total_pages = int(data.get("PaginationResult", {}).get("TotalNumberOfPages", 1))
                print(f"Page {page}/{total_pages} — {len(txns)} transactions")

                for txn in txns:
                    item = txn["Item"]
                    item_id = item["ItemID"]
                    sold_date = txn["CreatedDate"]

                    if sale_exists(cursor, item_id, sold_date):
                        continue

                    paid = txn.get("AmountPaid", {})
                    sale_price = float(paid.get("value", 0)) if paid else 0
                    if sale_price <= 0:
                        continue

                    title = item.get("Title", "")
                    if "NEW" in title.upper():
                        continue

                    listing = item.get("ListingDetails", {})

                    sale = {
                        "item_id": item_id,
                        "title": title,
                        "listing_start_date": listing.get("StartTime"),
                        "sold_date": sold_date,
                        "quantity": int(txn.get("QuantityPurchased", 1)),
                        "sale_price_total": round(sale_price, 2),
                        "final_value_fee": round(float(txn.get("FinalValueFee", {}).get("value", "0")), 2),
                    }

                    insert_sale(cursor, sale)
                    new_sales += 1

                if page >= total_pages:
                    break

                page += 1
                time.sleep(0.75)

            except Exception as e:
                msg = str(e)
                if "406" in msg or "30 day maximum" in msg:
                    print("Time window too large — skipping chunk")
                else:
                    print(f"API Error: {msg}")
                time.sleep(10)
                break

        current = chunk_end + timedelta(seconds=1)
        time.sleep(1)

    conn.commit()
    conn.close()

    print(f"\nDone! Added {new_sales:,} new sales.")
    print(f"Total records now: {existing_count + new_sales:,}")


if __name__ == "__main__":
    main()