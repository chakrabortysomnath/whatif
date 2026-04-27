import streamlit as st
import streamlit.components.v1 as components
import json
import pathlib
from auth import check_password
from data import load_state, save_state, reset_state

st.set_page_config(
    page_title="Portfolio What-If",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Hide Streamlit default chrome ──────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding: 0 !important; max-width: 100% !important;}
    .stApp {overflow: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Password gate ──────────────────────────────────────────────────────────
if not check_password():
    st.stop()

# ── Handle save request from dashboard (via query param) ──────────────────
if "save_state" in st.query_params:
    raw = st.query_params.get("save_state", "")
    if raw:
        try:
            state = json.loads(raw)
            ok = save_state(state)
            st.session_state["last_save_ok"] = ok
        except Exception as e:
            st.session_state["last_save_ok"] = False
        # Clear the query param and rerun cleanly
        st.query_params.clear()
        st.rerun()

# ── Handle reset request ──────────────────────────────────────────────────
if "reset" in st.query_params:
    reset_state()
    st.query_params.clear()
    st.session_state.pop("last_save_ok", None)
    st.rerun()

# ── Load persisted state ──────────────────────────────────────────────────
saved = load_state()
state_json = json.dumps(saved, ensure_ascii=False)

# Show save confirmation if just saved
if st.session_state.pop("last_save_ok", None) is True:
    st.success("✅ State saved successfully", icon="✅")
elif st.session_state.pop("last_save_ok", None) is False:
    st.error("⚠️ Failed to save state")

# ── Load dashboard HTML ───────────────────────────────────────────────────
html_path = pathlib.Path(__file__).parent / "dashboard.html"
if not html_path.exists():
    st.error("dashboard.html not found. Please place it in the same folder as app.py.")
    st.stop()

html = html_path.read_text(encoding="utf-8")

# ── Inject saved state + save/restore JS into the HTML ───────────────────
save_js = f"""
<script>
// ── Saved state injected by Streamlit ──
window.__SAVED_STATE__ = {state_json};

// ── Save function: encodes state into query param → Streamlit reads it ──
function saveState(){{
    try {{
        const p = getP();
        const state = {{
            ctsh: p.ctsh,
            usdinr: p.usdinr,
            gbpinr: p.gbpinr,
            sgdinr: p.sgdinr,
            ret: p.ret * 100,
            fa: p.fa / 1e7,
            facoa: p.facoa / 1e7,
            fatax: p.fatax * 100,
            gw: p.gw / 1e5,
            gwcoa: p.gwcoa / 1e5,
            gwtax: p.gwtax * 100,
            msr: p.msr,
            eq: p.eq,
            sgdc: p.sgdc,
            inrc: p.inrc / 1e5,
            inreq: p.inreq / 1e5,
            propval: p.propval / 1e5,
            propyr: p.propyr,
            absli: p.absli / 1e5,
            absliyr: p.absliyr,
            grat: p.grat / 1e5,
            gratdelay: p.gratdelay,
            emplOn: p.emplOn,
            emplEnd: document.getElementById('empl-end') ? document.getElementById('empl-end').value : '1228',
            msrMo: p.msrMo,
            monthlyExp: window.monthlyExp || [],
            quarterlyExp: window.quarterlyExp || [],
            rsuSchedule: window.rsuSchedule || [],
            raiRows: window.raiRows || [],
            neilRows: window.neilRows || []
        }};
        const encoded = encodeURIComponent(JSON.stringify(state));
        // Navigate to save endpoint — Streamlit picks it up on reload
        window.top.location.href = window.top.location.pathname + '?save_state=' + encoded;
    }} catch(e) {{
        alert('Save failed: ' + e.message);
    }}
}}

function resetState(){{
    if(confirm('Reset all inputs to defaults? This cannot be undone.')){{
        window.top.location.href = window.top.location.pathname + '?reset=1';
    }}
}}

// ── Restore saved state after DOM is ready ──
document.addEventListener('DOMContentLoaded', function(){{
    const s = window.__SAVED_STATE__;
    if(!s || !Object.keys(s).length) return;

    function setVal(id, v){{
        const el = document.getElementById(id);
        if(el && v != null) el.value = v;
    }}
    function setSyncPair(id, v){{
        setVal(id, v);
        setVal(id + '-n', v);
    }}

    // Top bar sliders
    setSyncPair('ctsh',    s.ctsh);
    setSyncPair('usdinr',  s.usdinr);
    setSyncPair('gbpinr',  s.gbpinr);
    setSyncPair('sgdinr',  s.sgdinr);
    setSyncPair('ret',     s.ret);

    // Asset inputs
    ['fa','facoa','fatax','gw','gwcoa','gwtax',
     'inrc','inreq','propval','propyr','absli','absliyr','grat','gratdelay'].forEach(k => setVal(k, s[k]));

    // SGD assets (stored as raw numbers)
    setVal('msr', s.msr);
    setVal('eq',  s.eq);
    setVal('sgdc', s.sgdc);

    // Employment toggle
    const chip = document.getElementById('chip-empl');
    if(chip) {{
        if(s.emplOn === false) chip.classList.remove('on');
        else chip.classList.add('on');
    }}
    setVal('empl-end', s.emplEnd);

    // MSR months
    if(s.msrMo) {{
        Object.entries(s.msrMo).forEach(([yr, v]) => setVal('msr-mo-' + yr, v));
    }}

    // Restore array data into JS variables
    if(s.monthlyExp  && s.monthlyExp.length)  window.monthlyExp  = s.monthlyExp;
    if(s.quarterlyExp && s.quarterlyExp.length) window.quarterlyExp = s.quarterlyExp;
    if(s.rsuSchedule && s.rsuSchedule.length) window.rsuSchedule = s.rsuSchedule;
    if(s.raiRows     && s.raiRows.length)     window.raiRows     = s.raiRows;
    if(s.neilRows    && s.neilRows.length)    window.neilRows    = s.neilRows;

    // Re-render everything with restored values
    if(typeof renderAllTables === 'function') renderAllTables();
    if(typeof update === 'function') update();
}});
</script>
"""

# ── Add Save + Reset buttons to top bar ──────────────────────────────────
save_btn_html = """
    <button class="theme-btn" onclick="saveState()" style="background:var(--green-bg);border-color:var(--green-bdr);color:var(--green)">💾 Save</button>
    <button class="theme-btn" onclick="resetState()" style="margin-left:4px">↺ Reset</button>
"""

# Inject save JS before </head> and save buttons before theme button
html = html.replace("</head>", save_js + "\n</head>", 1)
html = html.replace(
    '<button class="theme-btn" onclick="toggleTheme()" id="theme-btn">Dark mode</button>',
    save_btn_html + '\n    <button class="theme-btn" onclick="toggleTheme()" id="theme-btn">Dark mode</button>'
)

# ── Render the dashboard ─────────────────────────────────────────────────
# Height set tall enough to show all sections without inner scroll
components.html(html, height=5500, scrolling=True)
