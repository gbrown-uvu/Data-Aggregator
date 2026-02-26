"""
Creates the SQLite database for storing eBay sales data if it doesn't exist.
"""

import sqlite3
from pathlib import Path

DB_FILE = "ebay_sales.db"


def create_db() -> None:
    db_path = Path(DB_FILE)
    if db_path.exists():
        print(f"Database already exists: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE sales (
            item_id           TEXT    NOT NULL,
            sold_date         TEXT    NOT NULL,
            title             TEXT,
            listing_start_date TEXT,
            quantity          INTEGER DEFAULT 1,
            sale_price_total  REAL,
            final_value_fee   REAL,
            PRIMARY KEY (item_id, sold_date)
        )
    """)

    # Performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sold_date ON sales(sold_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title    ON sales(title)")

    conn.commit()
    conn.close()
    print(f"Database created successfully: {DB_FILE}")


if __name__ == "__main__":
    create_db()