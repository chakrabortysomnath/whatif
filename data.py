import json
import pathlib

STATE_FILE = pathlib.Path(__file__).parent / "data" / "user_state.json"

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
    "swpRate": 0.08
}

def load_state() -> dict:
    """Load user state from JSON file, falling back to defaults."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            # Merge with defaults so new keys are always present
            merged = DEFAULT_STATE.copy()
            merged.update(saved)
            return merged
        except Exception:
            pass
    return DEFAULT_STATE.copy()

def save_state(state: dict) -> bool:
    """Save user state to JSON file. Returns True on success."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False

def reset_state() -> bool:
    """Reset to default state."""
    return save_state(DEFAULT_STATE.copy())
