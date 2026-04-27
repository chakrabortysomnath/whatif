# Portfolio What-If Dashboard — Streamlit Deployment Plan

## Architecture

```
portfolio-whatif/
├── app.py                  # Streamlit entry point
├── auth.py                 # Password protection
├── data.py                 # JSON persistence (load/save user state)
├── dashboard.html          # The HTML dashboard (copied from current build)
├── data/
│   └── user_state.json     # Persisted user inputs (gitignored)
├── requirements.txt
├── render.yaml             # Render deploy config
└── .gitignore
```

## How it works

1. User hits the Streamlit URL → sees a login screen
2. On correct password → Streamlit loads app.py
3. app.py reads user_state.json → injects saved values into dashboard.html
4. st.components.v1.html() renders the full HTML dashboard at full height
5. A "Save" button in the dashboard calls window.parent.postMessage() to send
   current state back to Streamlit → app.py writes to user_state.json
6. On next load, saved values are pre-filled in all inputs

## Files

### app.py
```python
import streamlit as st
import streamlit.components.v1 as components
from auth import check_password
from data import load_state, save_state
import json, pathlib

st.set_page_config(
    page_title="Portfolio What-If",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Password gate ---
if not check_password():
    st.stop()

# --- Load persisted state ---
saved = load_state()

# --- Load and inject HTML ---
html_path = pathlib.Path(__file__).parent / "dashboard.html"
html = html_path.read_text(encoding="utf-8")

# Inject saved state as a JS variable so dashboard can restore inputs on load
state_json = json.dumps(saved)
inject = f"<script>window.__SAVED_STATE__ = {state_json};</script>"
html = html.replace("</head>", inject + "\n</head>", 1)

# --- Render dashboard ---
components.html(html, height=4000, scrolling=True)

# --- Handle save messages from dashboard ---
# Dashboard calls window.parent.postMessage({type:'save', state:{...}}, '*')
# Streamlit receives this via query params workaround (see data.py notes)
if "state" in st.query_params:
    raw = st.query_params["state"]
    try:
        state = json.loads(raw)
        save_state(state)
        st.query_params.clear()
        st.success("State saved!", icon="✅")
    except Exception:
        pass
```

### auth.py
```python
import streamlit as st
import hmac

def check_password() -> bool:
    """Returns True if the user entered the correct password."""
    
    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"],
            st.secrets["PASSWORD"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("## 📊 Portfolio What-If Dashboard")
    st.text_input(
        "Password",
        type="password",
        on_change=password_entered,
        key="password",
        placeholder="Enter access password"
    )
    if "password_correct" in st.session_state:
        st.error("Incorrect password")
    return False
```

### data.py
```python
import json, pathlib, os

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
    "msrMo": {"2026":7,"2027":12,"2028":12,"2029":5},
    "monthlyExp": [],   # populated from defaults if empty
    "quarterlyExp": [],
    "rsuSchedule": [],
    "raiRows": [],
    "neilRows": []
}

def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_STATE.copy()

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
```

### requirements.txt
```
streamlit>=1.35.0
```

### render.yaml
```yaml
services:
  - type: web
    name: portfolio-whatif
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
    envVars:
      - key: PASSWORD
        sync: false   # Set in Render dashboard — never commit to git
```

### .gitignore
```
data/
*.json
.streamlit/secrets.toml
__pycache__/
*.pyc
```

### .streamlit/secrets.toml  (local dev only, never commit)
```toml
PASSWORD = "your-secret-password-here"
```

## Dashboard HTML changes needed

Add these two blocks to dashboard.html:

### 1. On load — restore saved state
In the script section, after renderAllTables(); update();:
```javascript
// Restore saved state from Streamlit injection
if(window.__SAVED_STATE__ && Object.keys(window.__SAVED_STATE__).length > 0){
    const s = window.__SAVED_STATE__;
    // Restore sliders + number inputs
    ['ctsh','usdinr','gbpinr','sgdinr','ret'].forEach(k=>{
        if(s[k]!=null){
            const sl=document.getElementById(k);
            const inp=document.getElementById(k+'-n');
            if(sl) sl.value=s[k];
            if(inp) inp.value=s[k];
        }
    });
    // Restore number-only inputs
    ['fa','facoa','fatax','gw','gwcoa','gwtax','msr','eq','sgdc','inrc','inreq',
     'propval','propyr','absli','absliyr','grat','gratdelay'].forEach(k=>{
        const el=document.getElementById(k);
        if(el && s[k]!=null) el.value=s[k];
    });
    // Restore employment toggle
    if(s.emplOn===false) document.getElementById('chip-empl').classList.remove('on');
    if(s.emplEnd) document.getElementById('empl-end').value=s.emplEnd;
    // Restore MSR months
    if(s.msrMo) Object.entries(s.msrMo).forEach(([yr,v])=>{
        const el=document.getElementById('msr-mo-'+yr);
        if(el) el.value=v;
    });
    // Restore expense arrays
    if(s.monthlyExp && s.monthlyExp.length) monthlyExp=s.monthlyExp;
    if(s.quarterlyExp && s.quarterlyExp.length) quarterlyExp=s.quarterlyExp;
    if(s.rsuSchedule && s.rsuSchedule.length) rsuSchedule=s.rsuSchedule;
    if(s.raiRows && s.raiRows.length) raiRows=s.raiRows;
    if(s.neilRows && s.neilRows.length) neilRows=s.neilRows;
    renderAllTables();
    update();
}
```

### 2. Save button — send state to Streamlit
Add a save button to the top bar (next to theme button):
```javascript
function saveState(){
    const p = getP();
    const state = {
        ...p,
        emplEnd: document.getElementById('empl-end').value,
        monthlyExp, quarterlyExp, rsuSchedule, raiRows, neilRows
    };
    // Encode state into URL query param → Streamlit reads it
    const encoded = encodeURIComponent(JSON.stringify(state));
    window.location.href = window.location.pathname + '?state=' + encoded;
}
```
HTML button in top bar:
```html
<button class="theme-btn" onclick="saveState()">💾 Save</button>
```

## Deployment steps on Render

1. Push code to a GitHub repo (private recommended)
2. Go to render.com → New Web Service → Connect GitHub repo
3. Set environment variable PASSWORD in Render dashboard
4. Deploy — Render auto-detects Python, runs startCommand
5. Your URL: https://portfolio-whatif.onrender.com

## Local development

```bash
# Install
pip install streamlit

# Create secrets
mkdir .streamlit
echo 'PASSWORD = "test123"' > .streamlit/secrets.toml

# Run
streamlit run app.py
```

## Limitations to be aware of

- st.components.v1.html() runs in an iframe — postMessage state saving
  works but requires the URL redirect workaround (see data.py notes)
- Render free tier spins down after 15min inactivity — first load takes ~30s
  Upgrade to Render Starter ($7/mo) for always-on
- data/user_state.json lives on the Render ephemeral filesystem —
  it resets on every deploy. For true persistence across deploys,
  swap data.py to use a Render PostgreSQL or external JSON store (e.g. JSONBin)
