import sqlite3
import json
import pathlib
from datetime import datetime
from typing import Dict, Any

# Database file location
DB_FILE = pathlib.Path(__file__).parent / "data" / "portfolio.db"

# Default state template (fallback if DB is empty)
DEFAULT_STATE = {
    "ctsh": 55,
    "usdinr": 94.19,
    "gbpinr": 119.44,
    "sgdinr": 73.76,
    "ret": 7.0,
    "fa": 4.2,
    "facoa": 1.5,
    "fatax": 30,
    "gw": 45,
    "gwcoa": 35,
    "gwtax": 30,
    "msr": 480000,
    "eq": 131000,
    "sgdc": 70000,
    "inrc": 17,
    "inreq": 14,
    "propval": 80,
    "propyr": 2027,
    "absli": 21,
    "absliyr": 2031,
    "grat": 50,
    "gratdelay": 6,
    "emplOn": True,
    "emplEnd": "1228",
    "msrMo": {"2026": 7, "2027": 12, "2028": 12, "2029": 5},
    "monthlyExp": [],
    "quarterlyExp": [],
    "rsuSchedule": [],
    "raiRows": [],
    "neilRows": [],
    "swpAsset": "none",
    "swpMonthly": 50000,
    "swpStartYr": 2026,
    "swpRate": 0.08,
    "oneOffRows": []
}


def init_db():
    """Initialize database and create tables if they don't exist."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create user_state table (key-value storage for all configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create history table (track changes for audit/recovery)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create backup table (automatic backups)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def load_state() -> dict:
    """Load user state from SQLite database, falling back to defaults."""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get all key-value pairs from database
    cursor.execute("SELECT key, value FROM user_state")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        # Database is empty, return defaults
        return DEFAULT_STATE.copy()

    # Parse saved state
    saved_state = {}
    for key, value in rows:
        try:
            # Try to parse as JSON (for complex types like arrays, objects)
            saved_state[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Fall back to string or number
            try:
                saved_state[key] = float(value) if '.' in value else int(value)
            except (ValueError, TypeError):
                saved_state[key] = value

    # Merge with defaults (ensures new keys are present)
    merged = DEFAULT_STATE.copy()
    merged.update(saved_state)
    return merged


def save_state(state: dict) -> bool:
    """Save user state to SQLite database with history tracking."""
    try:
        init_db()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get current state to track changes
        cursor.execute("SELECT key, value FROM user_state")
        old_state = {k: v for k, v in cursor.fetchall()}

        # Save/update each key-value pair
        for key, value in state.items():
            # Convert complex types to JSON strings
            if isinstance(value, (dict, list)):
                json_value = json.dumps(value, ensure_ascii=False)
            else:
                json_value = str(value)

            # Get old value for history
            old_value = old_state.get(key)

            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO user_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json_value))

            # Track change in history (if value changed)
            if key not in old_state or old_value != json_value:
                cursor.execute("""
                    INSERT INTO state_history (key, old_value, new_value)
                    VALUES (?, ?, ?)
                """, (key, old_value, json_value))

        # Create automatic backup (keep last 10 backups)
        cursor.execute("""
            INSERT INTO backups (backup_data)
            VALUES (?)
        """, (json.dumps(state, ensure_ascii=False),))

        # Delete old backups (keep only last 10)
        cursor.execute("""
            DELETE FROM backups
            WHERE id NOT IN (
                SELECT id FROM backups ORDER BY created_at DESC LIMIT 10
            )
        """)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False


def reset_state() -> bool:
    """Reset database to default state."""
    try:
        init_db()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Clear user_state table
        cursor.execute("DELETE FROM user_state")

        # Insert defaults
        for key, value in DEFAULT_STATE.items():
            if isinstance(value, (dict, list)):
                json_value = json.dumps(value, ensure_ascii=False)
            else:
                json_value = str(value)

            cursor.execute("""
                INSERT INTO user_state (key, value)
                VALUES (?, ?)
            """, (key, json_value))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error resetting state: {e}")
        return False


def get_history(key: str = None, limit: int = 50) -> list:
    """Get change history for a specific key or all keys."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if key:
        cursor.execute("""
            SELECT key, old_value, new_value, changed_at
            FROM state_history
            WHERE key = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (key, limit))
    else:
        cursor.execute("""
            SELECT key, old_value, new_value, changed_at
            FROM state_history
            ORDER BY changed_at DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "key": row[0],
            "old_value": row[1],
            "new_value": row[2],
            "changed_at": row[3]
        }
        for row in rows
    ]


def get_backup(backup_id: int = None) -> dict:
    """Get a specific backup or the latest backup."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if backup_id:
        cursor.execute("""
            SELECT backup_data FROM backups WHERE id = ?
        """, (backup_id,))
    else:
        cursor.execute("""
            SELECT backup_data FROM backups ORDER BY created_at DESC LIMIT 1
        """)

    result = cursor.fetchone()
    conn.close()

    if result:
        return json.loads(result[0])
    return {}


def restore_backup(backup_id: int) -> bool:
    """Restore a specific backup."""
    init_db()
    backup_data = get_backup(backup_id)

    if backup_data:
        return save_state(backup_data)
    return False


def get_db_stats() -> dict:
    """Get database statistics."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM user_state")
    state_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM state_history")
    history_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM backups")
    backup_count = cursor.fetchone()[0]

    cursor.execute("SELECT size FROM pragma_database_list WHERE name='main'")
    try:
        db_size = cursor.fetchone()[0]
    except:
        db_size = DB_FILE.stat().st_size if DB_FILE.exists() else 0

    conn.close()

    return {
        "state_entries": state_count,
        "history_entries": history_count,
        "backups": backup_count,
        "db_size_bytes": db_size
    }


# Initialize database on module load
init_db()
