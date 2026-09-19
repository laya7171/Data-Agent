from pathlib import Path
import csv
import sqlite3


# =========================================================
# PATHS
# =========================================================

# create_db.py is inside:
# Data Agent/utils/

# Move from utils/ to the project root:
BASE_DIR = Path(__file__).resolve().parent.parent

# Database folder:
# Data Agent/data/
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)

# SQLite database file:
DB_PATH = DB_DIR / "agent.db"

# CSV folder:
# Data Agent/csv_data/
CSV_DIR = BASE_DIR / "csv_data"


print(f"Database path: {DB_PATH}")
print(f"CSV folder: {CSV_DIR}")


# =========================================================
# DATABASE CONNECTION
# =========================================================

conn = sqlite3.connect(DB_PATH)

# Enable foreign-key validation
conn.execute("PRAGMA foreign_keys = ON")

cursor = conn.cursor()


# =========================================================
# CREATE TABLES FIRST
# =========================================================

create_tables_sql = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    city TEXT,
    province TEXT,
    user_type TEXT NOT NULL,
    signup_date TEXT,
    is_active INTEGER
);

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY,
    driver_id INTEGER NOT NULL,
    make TEXT,
    model TEXT,
    year INTEGER,
    license_plate TEXT UNIQUE,
    color TEXT,
    is_active INTEGER,

    FOREIGN KEY (driver_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS rides (
    ride_id INTEGER PRIMARY KEY,
    rider_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    requested_at TEXT,
    pickup_time TEXT,
    dropoff_time TEXT,
    pickup_latitude REAL,
    pickup_longitude REAL,
    dropoff_latitude REAL,
    dropoff_longitude REAL,
    distance_km REAL,
    fare REAL,
    surge_multiplier REAL,
    status TEXT,
    cancellation_reason TEXT,

    FOREIGN KEY (rider_id)
        REFERENCES users(user_id),

    FOREIGN KEY (driver_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount REAL,
    payment_method TEXT,
    payment_status TEXT,
    transaction_id TEXT UNIQUE,
    payment_time TEXT,

    FOREIGN KEY (ride_id)
        REFERENCES rides(ride_id),

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    rating INTEGER,
    comment TEXT,
    rated_at TEXT,

    FOREIGN KEY (ride_id)
        REFERENCES rides(ride_id),

    FOREIGN KEY (rider_id)
        REFERENCES users(user_id),

    FOREIGN KEY (driver_id)
        REFERENCES users(user_id),

    CHECK (rating BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_vehicles_driver_id
ON vehicles(driver_id);

CREATE INDEX IF NOT EXISTS idx_rides_rider_id
ON rides(rider_id);

CREATE INDEX IF NOT EXISTS idx_rides_driver_id
ON rides(driver_id);

CREATE INDEX IF NOT EXISTS idx_rides_requested_at
ON rides(requested_at);

CREATE INDEX IF NOT EXISTS idx_rides_status
ON rides(status);

CREATE INDEX IF NOT EXISTS idx_payments_ride_id
ON payments(ride_id);

CREATE INDEX IF NOT EXISTS idx_payments_user_id
ON payments(user_id);

CREATE INDEX IF NOT EXISTS idx_ratings_ride_id
ON ratings(ride_id);

CREATE INDEX IF NOT EXISTS idx_ratings_driver_id
ON ratings(driver_id);
"""

# IMPORTANT: create tables before loading CSV files
conn.executescript(create_tables_sql)

print("Tables created successfully")


# =========================================================
# LOAD CSV DATA
# =========================================================

def load_csv(table_name, csv_file, columns):
    file_path = CSV_DIR / csv_file

    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    column_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)

    insert_sql = f"""
        INSERT INTO {table_name} ({column_names})
        VALUES ({placeholders})
    """

    rows = []

    with open(
        file_path,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for csv_row in reader:
            values = []

            for column in columns:
                value = csv_row[column]

                # Empty CSV values become SQL NULL
                if value == "":
                    value = None

                values.append(value)

            rows.append(tuple(values))

    cursor.executemany(insert_sql, rows)

    print(f"Loaded {len(rows):,} records from {csv_file}")


# =========================================================
# LOAD TABLES
# =========================================================

load_csv(
    "users",
    "users.csv",
    [
        "user_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "city",
        "province",
        "user_type",
        "signup_date",
        "is_active",
    ],
)

load_csv(
    "vehicles",
    "vehicles.csv",
    [
        "vehicle_id",
        "driver_id",
        "make",
        "model",
        "year",
        "license_plate",
        "color",
        "is_active",
    ],
)

load_csv(
    "rides",
    "rides.csv",
    [
        "ride_id",
        "rider_id",
        "driver_id",
        "requested_at",
        "pickup_time",
        "dropoff_time",
        "pickup_latitude",
        "pickup_longitude",
        "dropoff_latitude",
        "dropoff_longitude",
        "distance_km",
        "fare",
        "surge_multiplier",
        "status",
        "cancellation_reason",
    ],
)

load_csv(
    "payments",
    "payments.csv",
    [
        "payment_id",
        "ride_id",
        "user_id",
        "amount",
        "payment_method",
        "payment_status",
        "transaction_id",
        "payment_time",
    ],
)

load_csv(
    "ratings",
    "ratings.csv",
    [
        "rating_id",
        "ride_id",
        "rider_id",
        "driver_id",
        "rating",
        "comment",
        "rated_at",
    ],
)


# =========================================================
# VERIFY COUNTS
# =========================================================

tables = [
    "users",
    "vehicles",
    "rides",
    "payments",
    "ratings",
]

print("\nRecord counts:")
print("-" * 40)

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table:<15} {count:>10,}")


# =========================================================
# COMMIT AND CLOSE
# =========================================================

conn.commit()
cursor.close()
conn.close()

print("\nData loaded successfully!")
print(f"Database saved at: {DB_PATH}")