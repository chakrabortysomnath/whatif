from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature
import pathlib
import json
import os
import time
import requests as http
from data import load_state, save_state, reset_state

app = FastAPI()

BASE         = pathlib.Path(__file__).parent
PASSWORD     = os.environ.get("PASSWORD", "")
SECRET_KEY   = os.environ.get("SECRET_KEY", "dev-secret-change-me")
COOKIE_NAME  = "wif_session"
COOKIE_TTL   = 86400 * 30          # 30 days

signer = URLSafeTimedSerializer(SECRET_KEY)

# ── CTSH price cache ──────────────────────────────────────────────────────
_price: dict = {"v": 54, "ts": 0.0}

def get_ctsh_price() -> int:
    now = time.time()
    if now - _price["ts"] < 300:          # cached for 5 min
        return _price["v"]
    try:
        r = http.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/CTSH",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        r.raise_for_status()
        price = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if price and price > 0:
            _price["v"] = max(30, min(90, int(round(price))))
            _price["ts"] = now
    except Exception:
        pass
    return _price["v"]


# ── Auth helpers ──────────────────────────────────────────────────────────
def is_auth(request: Request) -> bool:
    try:
        signer.loads(request.cookies.get(COOKIE_NAME, ""), max_age=COOKIE_TTL)
        return True
    except (BadSignature, Exception):
        return False


# ── Login page HTML ───────────────────────────────────────────────────────
def login_html(error: bool = False) -> str:
    err_block = '<p class="err">Incorrect password. Please try again.</p>' if error else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio What-If – Login</title>
<style>
  *{{box-sizing:border-box}}
  body{{font-family:system-ui,sans-serif;background:#f0f2f5;display:flex;
       align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .card{{background:#fff;border-radius:14px;padding:48px 40px 40px;
         box-shadow:0 4px 24px rgba(0,0,0,.08);width:340px;text-align:center}}
  .icon{{font-size:44px;margin-bottom:8px}}
  h1{{font-size:22px;font-weight:700;margin:0 0 4px}}
  .sub{{color:#888;font-size:14px;margin:0 0 28px}}
  input{{width:100%;padding:11px 14px;font-size:15px;border:1.5px solid #ddd;
         border-radius:9px;outline:none;transition:border .2s}}
  input:focus{{border-color:#4f8ef7}}
  button{{margin-top:14px;width:100%;padding:12px;font-size:15px;font-weight:600;
          background:#4f8ef7;color:#fff;border:none;border-radius:9px;cursor:pointer;
          transition:background .2s}}
  button:hover{{background:#3a7be0}}
  .err{{color:#c0392b;font-size:13px;margin-top:12px;margin-bottom:0}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">📊</div>
  <h1>Portfolio What-If</h1>
  <p class="sub">Personal financial scenario modeller</p>
  <form method="post" action="/login">
    <input type="password" name="password" placeholder="Enter access password" autofocus>
    <button type="submit">Sign in</button>
    {err_block}
  </form>
</div>
</body></html>"""


# ── Routes ────────────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(login_html())


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == PASSWORD:
        token = signer.dumps("ok")
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=COOKIE_TTL)
        return resp
    return HTMLResponse(login_html(error=True), status_code=401)


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_auth(request):
        return RedirectResponse("/login")

    html = (BASE / "dashboard.html").read_text(encoding="utf-8")

    # ── Inject live CTSH price ─────────────────────────────────────────
    ctsh_live = get_ctsh_price()
    html = html.replace(
        '<input type="range" id="ctsh" min="30" max="90" step="1" value="54">',
        f'<input type="range" id="ctsh" min="30" max="90" step="1" value="{ctsh_live}">',
    )
    html = html.replace(
        '<input type="number" id="ctsh-n" value="54" min="30" max="90">',
        f'<input type="number" id="ctsh-n" value="{ctsh_live}" min="30" max="90">',
    )
    html = html.replace(
        '<span class="tb-val" id="v-ctsh">$54</span>',
        f'<span class="tb-val" id="v-ctsh">${ctsh_live}</span>',
    )

    # ── Inject state + JS ──────────────────────────────────────────────
    saved      = load_state()
    state_json = json.dumps(saved, ensure_ascii=False)

    inject_js = f"""<script>
window.__SAVED_STATE__ = {state_json};

async function saveState() {{
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
        const r = await fetch('/api/save', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(state)
        }});
        const d = await r.json();
        showToast(d.ok ? '✅ Saved!' : '⚠️ Save failed', d.ok);
    }} catch(e) {{
        showToast('⚠️ ' + e.message, false);
    }}
}}

async function resetState() {{
    if (!confirm('Reset all inputs to defaults? This cannot be undone.')) return;
    try {{
        const r = await fetch('/api/reset', {{ method: 'POST' }});
        const d = await r.json();
        if (d.ok) location.reload();
        else showToast('⚠️ Reset failed', false);
    }} catch(e) {{
        showToast('⚠️ ' + e.message, false);
    }}
}}

function showToast(msg, ok) {{
    let t = document.getElementById('__wif_toast__');
    if (!t) {{
        t = document.createElement('div');
        t.id = '__wif_toast__';
        t.style.cssText = 'position:fixed;top:16px;right:20px;padding:10px 18px;border-radius:8px;'
            + 'font-size:14px;font-weight:600;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none';
        document.body.appendChild(t);
    }}
    t.textContent = msg;
    t.style.background = ok ? '#d4edda' : '#f8d7da';
    t.style.color      = ok ? '#155724' : '#721c24';
    t.style.opacity    = '1';
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.style.opacity = '0', 3000);
}}

document.addEventListener('DOMContentLoaded', function() {{
    const s = window.__SAVED_STATE__;
    if (!s || !Object.keys(s).length) return;

    function setVal(id, v) {{
        const el = document.getElementById(id);
        if (el && v != null) el.value = v;
    }}
    function setSyncPair(id, v) {{ setVal(id, v); setVal(id + '-n', v); }}

    setSyncPair('ctsh',   s.ctsh);
    setSyncPair('usdinr', s.usdinr);
    setSyncPair('gbpinr', s.gbpinr);
    setSyncPair('sgdinr', s.sgdinr);
    setSyncPair('ret',    s.ret);

    ['fa','facoa','fatax','gw','gwcoa','gwtax',
     'inrc','inreq','propval','propyr','absli','absliyr','grat','gratdelay']
        .forEach(k => setVal(k, s[k]));

    setVal('msr',  s.msr);
    setVal('eq',   s.eq);
    setVal('sgdc', s.sgdc);

    const chip = document.getElementById('chip-empl');
    if (chip) {{
        if (s.emplOn === false) chip.classList.remove('on');
        else chip.classList.add('on');
    }}
    setVal('empl-end', s.emplEnd);

    if (s.msrMo) Object.entries(s.msrMo).forEach(([yr, v]) => setVal('msr-mo-' + yr, v));

    if (s.monthlyExp   && s.monthlyExp.length)   window.monthlyExp   = s.monthlyExp;
    if (s.quarterlyExp && s.quarterlyExp.length)  window.quarterlyExp = s.quarterlyExp;
    if (s.rsuSchedule  && s.rsuSchedule.length)   window.rsuSchedule  = s.rsuSchedule;
    if (s.raiRows      && s.raiRows.length)        window.raiRows      = s.raiRows;
    if (s.neilRows     && s.neilRows.length)       window.neilRows     = s.neilRows;

    if (typeof renderAllTables === 'function') renderAllTables();
    if (typeof update === 'function') update();
}});
</script>"""

    save_btn_html = """
    <button class="theme-btn" onclick="saveState()" style="background:var(--green-bg);border-color:var(--green-bdr);color:var(--green)">💾 Save</button>
    <button class="theme-btn" onclick="resetState()" style="margin-left:4px">↺ Reset</button>"""

    html = html.replace("</head>", inject_js + "\n</head>", 1)
    html = html.replace(
        '<button class="theme-btn" onclick="toggleTheme()" id="theme-btn">Dark mode</button>',
        save_btn_html + '\n    <button class="theme-btn" onclick="toggleTheme()" id="theme-btn">Dark mode</button>',
    )

    return HTMLResponse(html)


# ── API endpoints ─────────────────────────────────────────────────────────
@app.post("/api/save")
async def api_save(request: Request):
    if not is_auth(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    state = await request.json()
    return JSONResponse({"ok": save_state(state)})


@app.post("/api/reset")
async def api_reset(request: Request):
    if not is_auth(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    return JSONResponse({"ok": reset_state()})


@app.get("/api/ctsh")
async def api_ctsh(request: Request):
    if not is_auth(request):
        return JSONResponse({"ok": False}, status_code=401)
    return JSONResponse({"price": get_ctsh_price()})
