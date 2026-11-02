"""
RakshaScore - Cyber Risk Assessment Platform.
Run:  streamlit run app.py

Pages: Assessment | Dashboard | Score Explanation | Remediation | Reports | Methodology
Needs: config/schema.json and the three .pkl files in models/ (created by scripts/train_models.py).
"""
import inspect
import json
import re
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from rakshascore import insights as I, pipeline as P
from rakshascore.paths import RESULTS_DIR

st.set_page_config(page_title="RakshaScore | Cyber Risk Assessment Platform", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
STRETCH = {"width": "stretch"} if "width" in inspect.signature(st.button).parameters else {"use_container_width": True}
NAVY, BLUE = "#0F2A47", "#2563EB"
TIER_COLOR = I.TIER_COLOR

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { color-scheme: light; }
html, body, .stApp, [class*="css"] { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }
.stApp { background: #F3F5F9; }
.stApp p, .stApp li, [data-testid="stMarkdownContainer"] p { color: #1B2B3C; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; height: 2.2rem; }
.block-container { max-width: 100% !important; padding: 1rem 2.4rem 3rem 2.4rem; }

/* ---------- sidebar shell ---------- */
section[data-testid="stSidebar"] { background: #0B1F3A; border-right: 0; min-width: 270px; }
section[data-testid="stSidebar"] * { color: #C9D4E5; }
section[data-testid="stSidebar"] .logo { display: flex; align-items: center; gap: 11px; padding: 6px 4px 18px; border-bottom: 1px solid #1E3558; margin-bottom: 14px; }
section[data-testid="stSidebar"] .logo b { color: #fff; font-size: 1.15rem; display: block; line-height: 1.2; }
section[data-testid="stSidebar"] .logo small { color: #8FA5C2; font-size: .72rem; }
section[data-testid="stSidebar"] .sec { color: #6F87A8; font-size: .68rem; letter-spacing: 1.4px; font-weight: 700; margin: 16px 0 6px; }
section[data-testid="stSidebar"] [data-testid="stRadioGroup"] { flex-direction: column; gap: 2px; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] { width: 100%; padding: 9px 12px; border-radius: 8px; cursor: pointer; border-left: 3px solid transparent; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child { display: none; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: #12294A; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background: #17335C; border-left-color: #3B82F6; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { color: #fff !important; font-weight: 600; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] p { font-size: .93rem; color: #B8C7DB !important; }
section[data-testid="stSidebar"] input { background: #12294A !important; color: #fff !important; border: 1px solid #2A4570 !important; }
section[data-testid="stSidebar"] [data-baseweb="input"] { background: #12294A !important; border: 1px solid #2A4570 !important; border-radius: 8px; }
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"], section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] * { background: #12294A !important; color: #fff !important; }
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] { border: 1px solid #2A4570 !important; border-radius: 8px; }
section[data-testid="stSidebar"] [data-baseweb="input"] button { background: transparent !important; }
section[data-testid="stSidebar"] [data-baseweb="input"] svg { fill: #8FA5C2 !important; }
section[data-testid="stSidebar"] .stButton > button { background: #12294A; border: 1px solid #2A4570; color: #E6EDF7; border-radius: 8px; font-weight: 600; }
section[data-testid="stSidebar"] .stButton > button p { color: #E6EDF7 !important; }
section[data-testid="stSidebar"] .stButton > button:hover { border-color: #3B82F6; }
section[data-testid="stSidebar"] .chip { background: #12294A; border: 1px solid #2A4570; border-radius: 6px; padding: 3px 9px; font-size: .72rem; display: inline-block; margin-top: 4px; }

/* ---------- page header ---------- */
.ph { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; margin: 4px 0 18px; padding-bottom: 14px; border-bottom: 1px solid #DDE3EC; }
.ph .crumb { color: #667085; font-size: .78rem; font-weight: 500; letter-spacing: .3px; }
.ph h1 { margin: 2px 0 2px; font-size: 1.65rem; font-weight: 700; color: #0F2A47; letter-spacing: -.4px; }
.ph p { margin: 0; color: #667085; font-size: .92rem; max-width: 760px; }
.ph .chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.chipx { border: 1px solid #DDE3EC; background: #fff; color: #475467; border-radius: 6px; padding: 5px 11px; font-size: .76rem; font-weight: 600; }
.chipx.ok { background: #ECFDF3; border-color: #ABEFC6; color: #067647; } .chipx.warn { background: #FFFAEB; border-color: #FEDF89; color: #B54708; }

/* ---------- cards & kpis ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border: 1px solid #E3E8EF !important; border-radius: 12px; box-shadow: 0 1px 3px rgba(16,24,40,.06); }
.cardh { font-weight: 700; color: #0F2A47; font-size: 1rem; } .cards { color: #667085; font-size: .8rem; margin: 2px 0 10px; }
.kpi { background: #fff; border: 1px solid #E3E8EF; border-radius: 12px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(16,24,40,.06); border-top: 3px solid var(--c, #2563EB); height: 100%; }
.kpi .l { color: #667085; font-size: .7rem; text-transform: uppercase; letter-spacing: .8px; font-weight: 700; }
.kpi .v { font-size: 1.9rem; font-weight: 700; color: #0F2A47; line-height: 1.2; margin-top: 4px; }
.kpi .n { color: #667085; font-size: .8rem; margin-top: 2px; }
.badge { display: inline-block; padding: 4px 14px; border-radius: 99px; font-weight: 700; font-size: .8rem; color: #fff; letter-spacing: .5px; }
.st { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: .74rem; font-weight: 600; white-space: nowrap; }
.good { background: #DCFCE7; color: #166534; } .mid { background: #FEF3C7; color: #92400E; } .bad { background: #FEE2E2; color: #991B1B; } .info { background: #E0E7FF; color: #3730A3; }
.src { display: inline-block; font-size: .72rem; font-weight: 700; padding: 3px 9px; border-radius: 6px; background: #EEF4FF; color: #1D4ED8; margin-left: 8px; vertical-align: middle; }
.bar { height: 8px; background: #EDF0F4; border-radius: 99px; overflow: hidden; } .bar i { display: block; height: 100%; border-radius: 99px; }
.row { display: flex; align-items: center; gap: 12px; padding: 11px 0; border-bottom: 1px solid #EEF1F5; } .row:last-child { border-bottom: 0; }
.rank { flex: none; width: 26px; height: 26px; border-radius: 6px; background: #EEF4FF; color: #2563EB; font-weight: 700; display: grid; place-items: center; font-size: .8rem; }
.row .t { flex: 1; font-weight: 600; color: #1B2B3C; font-size: .9rem; } .row .t small { display: block; color: #667085; font-weight: 400; font-size: .76rem; }
.row .v { font-weight: 700; color: #DC2626; font-size: .92rem; min-width: 58px; text-align: right; }
.dom { margin: 11px 0; } .dom .lab { display: flex; justify-content: space-between; font-size: .85rem; color: #344054; font-weight: 500; margin-bottom: 5px; }
.note { background: #F8FAFC; border: 1px solid #E3E8EF; border-left: 3px solid #2563EB; border-radius: 6px; padding: 10px 14px; color: #475467; font-size: .82rem; margin: 10px 0; }
.lead { color: #1B2B3C; line-height: 1.7; font-size: .96rem; }
table.t { width: 100%; border-collapse: collapse; font-size: .85rem; } table.t th { background: #F8FAFC; color: #475467; text-align: left; padding: 9px 12px; font-size: .72rem; text-transform: uppercase; letter-spacing: .6px; border-bottom: 1px solid #DDE3EC; }
table.t td { padding: 10px 12px; border-bottom: 1px solid #EEF1F5; vertical-align: top; color: #1B2B3C; } table.t tr:hover td { background: #FAFBFD; } table.t small { color: #667085; }
.wf { position: relative; height: 14px; background: #F0F3F8; border-radius: 4px; } .wf i { position: absolute; top: 0; height: 100%; border-radius: 3px; }
.scale { display: flex; height: 12px; border-radius: 99px; overflow: hidden; margin: 14px 0 4px; position: relative; } .scale span { flex: 1; }
.scalelab { display: flex; justify-content: space-between; color: #667085; font-size: .72rem; }
.mark { position: absolute; top: -4px; width: 4px; height: 20px; background: #0F2A47; border-radius: 2px; }
.steps { display: flex; align-items: stretch; gap: 8px; } .step { flex: 1; border: 1px solid #E3E8EF; border-radius: 10px; padding: 12px; text-align: center; background: #FAFBFD; }
.step .l { font-size: .7rem; color: #667085; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; } .step .v { font-size: 1.6rem; font-weight: 700; color: #0F2A47; } .step .w { font-size: .72rem; color: #98A2B3; }
.arrow { align-self: center; color: #98A2B3; font-size: 1.2rem; }
.dd { display: grid; grid-template-columns: 150px 1fr; gap: 6px 14px; font-size: .88rem; } .dd b { color: #475467; font-weight: 600; } .dd div { color: #1B2B3C; line-height: 1.55; }

/* ---------- questionnaire ---------- */
.dhead { display: flex; align-items: center; gap: 14px; margin: 4px 0 6px; } .dcode { background: #0F2A47; color: #fff; font-weight: 700; border-radius: 8px; padding: 6px 12px; font-size: .9rem; letter-spacing: 1px; }
.dname { font-size: 1.15rem; font-weight: 700; color: #0F2A47; } .ddesc { color: #667085; font-size: .86rem; }
.thead { display: flex; padding: 8px 0; border-bottom: 2px solid #DDE3EC; color: #667085; font-size: .7rem; text-transform: uppercase; letter-spacing: .8px; font-weight: 700; margin-top: 10px; }
.ctl .cid { background: #EEF4FF; color: #1D4ED8; border-radius: 5px; padding: 2px 8px; font-weight: 700; font-size: .72rem; margin-right: 8px; } .ctl .ct { font-weight: 700; color: #0F2A47; font-size: .93rem; }
.ctl .cq { color: #1B2B3C; font-size: .9rem; margin-top: 5px; line-height: 1.45; } .ctl .cg { color: #667085; font-size: .78rem; margin-top: 4px; line-height: 1.45; }
.refs span { display: inline-block; background: #F2F4F7; color: #475467; border-radius: 5px; padding: 2px 8px; font-size: .7rem; font-weight: 600; margin: 0 5px 5px 0; }
.rowhr { border-top: 1px solid #EEF1F5; margin: 6px 0 8px; }
.st-key-assess [data-testid="stRadioGroup"] { gap: 0; flex-wrap: nowrap; }
.st-key-assess [data-testid="stRadioOption"] { border: 1px solid #D0D5DD; padding: 5px 14px; margin: 0 -1px 0 0; background: #fff; cursor: pointer; }
.st-key-assess [data-testid="stRadioOption"]:first-child { border-radius: 8px 0 0 8px; } .st-key-assess [data-testid="stRadioOption"]:last-child { border-radius: 0 8px 8px 0; }
.st-key-assess [data-testid="stRadioOption"] > div > div:first-child { display: none; } .st-key-assess [data-testid="stRadioOption"] p { font-size: .84rem; font-weight: 600; color: #475467 !important; }
.st-key-assess [data-testid="stRadioOption"][data-selected="true"] { background: #2563EB; border-color: #2563EB; } .st-key-assess [data-testid="stRadioOption"][data-selected="true"] p { color: #fff !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #DDE3EC; } .stTabs [data-baseweb="tab"] { padding: 10px 16px; } .stTabs [data-baseweb="tab"] p { font-weight: 600; font-size: .88rem; }
.stButton > button, .stDownloadButton > button { border-radius: 8px; border: 1px solid #D0D5DD; background: #fff; font-weight: 600; box-shadow: 0 1px 2px rgba(16,24,40,.05); }
.stButton > button p, .stDownloadButton > button p { color: #344054 !important; } .stButton > button:hover, .stDownloadButton > button:hover { border-color: #2563EB; }
.stButton > button[kind="primary"] { background: #2563EB; border-color: #2563EB; padding: .65rem 1.6rem; } .stButton > button[kind="primary"] p { color: #fff !important; } .stButton > button[kind="primary"]:hover { background: #1D4ED8; }
textarea, input { color: #1B2B3C !important; } [data-baseweb="select"] > div, [data-baseweb="input"] { background: #fff !important; } [data-baseweb="select"] * { color: #1B2B3C !important; }
</style>
"""


def H(markup):
    st.markdown(re.sub(r"\s*\n\s*", " ", markup.strip()), unsafe_allow_html=True)


esc = I.esc


H(CSS)

# =============================================================== state
NAV = {"Assessment": "edit_note", "Dashboard": "dashboard", "Score Explanation": "insights",
       "Remediation": "task_alt", "Reports": "description", "Methodology": "science"}
SHORT = {"PRF": "Profile", "IAM": "Identity", "NET": "Network", "END": "Endpoint", "VUL": "Vulnerability", "BCK": "Backup",
         "GOV": "Governance", "AWR": "Awareness", "DAT": "Data", "MON": "Monitoring", "TPR": "Third parties"}


def is_int_like(col):
    n = P.NUM[col]
    return all(float(n[k]).is_integer() for k in ("min", "max", "default"))


for col in P.COLUMNS:
    key = f"q_{col}"
    if key not in st.session_state:
        if col in P.CAT:
            st.session_state[key] = P.CAT[col]["default"]
        else:
            d = P.NUM[col]["default"]
            st.session_state[key] = int(d) if is_int_like(col) else float(d)
for k, v in dict(use_llm=P.llm_available(), desc="", view="Assessment", meta_org="", meta_assessor="", meta_scope="All business systems and data").items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("ref", "RS-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:4].upper())
if "_goto" in st.session_state:                         # page change requested by a button
    st.session_state["view"] = st.session_state.pop("_goto")


def read_record():
    return {col: st.session_state[f"q_{col}"] for col in P.COLUMNS}


def meta():
    return dict(org=st.session_state["meta_org"].strip() or "Unnamed organisation", ref=st.session_state["ref"],
                assessor=st.session_state["meta_assessor"].strip() or "Not specified", scope=st.session_state["meta_scope"].strip() or "Not specified")


def autofill():
    found, method = P.extract_factors(st.session_state["desc"], st.session_state["use_llm"])
    for col, val in found.items():
        st.session_state[f"q_{col}"] = (int(val) if is_int_like(col) else float(val)) if col in P.NUM else val
    err = f" AI error: {P.LAST_ERROR}" if P.LAST_ERROR and "fallback" in method else ""
    st.session_state["autofill_msg"] = f"{method}: {len(found)} questionnaire fields were populated. Please review them in the relevant tabs.{err}"


def reset_all():
    for k in [k for k in st.session_state if k.startswith(("q_", "fix_", "meta_")) or k in ("res", "ins", "autofill_msg", "_goto")]:
        del st.session_state[k]
    st.session_state.update(desc="", view="Assessment")


def _use_key():
    k = st.session_state.get("gem_key", "")
    if k.strip():
        P.set_provider_key("gemini", k)
        st.session_state["use_llm"] = True


# =============================================================== sidebar
with st.sidebar:
    H('<div class="logo"><svg width="34" height="34" viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3z" fill="#3B82F6"/>'
      '<path d="m8.8 12.2 2.4 2.4 4-4.4" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
      '<div><b>RakshaScore</b><small>Cyber Risk Assessment Platform</small></div></div><div class="sec">WORKSPACE</div>')
    st.radio("Navigation", list(NAV), key="view", label_visibility="collapsed", format_func=lambda v: f":material/{NAV[v]}:  {v}")
    H('<div class="sec">AI SERVICES</div>')
    st.text_input("Gemini API key (free)", type="password", key="gem_key", on_change=_use_key, placeholder="Paste key, press Enter")
    st.checkbox("Use AI for explanations", key="use_llm")
    if st.button("Test AI connection", **STRETCH):
        ok_, msg_ = P.test_llm()
        (st.success if ok_ else st.error)(msg_)
    H('<div class="sec">SESSION</div>')
    st.button("Reset assessment", on_click=reset_all, **STRETCH)
    H(f'<div style="margin-top:14px;color:#6F87A8;font-size:.72rem">Ref {st.session_state["ref"]}<br>Model: gradient-boosted trees + SHAP</div>')

view = st.session_state["view"]
prov = P.llm_provider()


def header(title, sub):
    ai = f'<span class="chipx ok">AI: {esc(prov)}</span>' if prov and st.session_state["use_llm"] else '<span class="chipx warn">AI: offline</span>'
    H(f'<div class="ph"><div><div class="crumb">RakshaScore &nbsp;/&nbsp; {esc(view)}</div><h1>{esc(title)}</h1><p>{esc(sub)}</p></div>'
      f'<div class="chips"><span class="chipx">{esc(meta()["org"])}</span><span class="chipx">{st.session_state["ref"]}</span>{ai}</div></div>')


def kpi(label, value, note="", color="#2563EB"):
    return f'<div class="kpi" style="--c:{color}"><div class="l">{label}</div><div class="v">{value}</div><div class="n">{note}</div></div>'


def need_results():
    if "res" not in st.session_state:
        header(view, "No assessment has been run yet.")
        H('<div class="note">Complete the questionnaire on the <b>Assessment</b> page and select <b>Run risk assessment</b>. '
          'This page will then show your results.</div>')
        return False
    return True


# =============================================================== page: assessment
def control_widget(col):
    key = f"q_{col}"
    title = I.KB[col]["title"]
    if col in P.CAT:
        opts = I.options(col)
        if len(opts) > 4:
            st.selectbox(title, opts, key=key, label_visibility="collapsed")
        else:
            st.radio(title, opts, key=key, horizontal=True, label_visibility="collapsed")
    else:
        n = P.NUM[col]
        if is_int_like(col):
            st.number_input(title, int(n["min"]), int(n["max"]) * 2, step=1, key=key, label_visibility="collapsed")
        else:
            st.number_input(title, float(n["min"]), float(n["max"]) * 2, step=0.5, key=key, label_visibility="collapsed")
    if col not in I.PROFILE_COLS:
        cls, lab = I.classify(col, st.session_state[key])
        H(f'<span class="st {cls}">{esc(lab)}</span>')


def control_row(col):
    kb = I.KB[col]
    c1, c2, c3 = st.columns([5.6, 2.3, 2.6], vertical_alignment="center") if "vertical_alignment" in inspect.signature(st.columns).parameters else st.columns([5.6, 2.3, 2.6])
    with c1:
        H(f'<div class="ctl"><span class="cid">{kb["id"]}</span><span class="ct">{esc(kb["title"])}</span>'
          f'<div class="cq">{esc(kb["q"])}</div><div class="cg">{esc(kb["guide"])}</div></div>')
    with c2:
        refs = [r.strip() for r in kb["refs"].split("·") if r.strip() and r.strip() != "-"]
        H('<div class="refs">' + ("".join(f"<span>{esc(r)}</span>" for r in refs) or '<span>-</span>') + "</div>")
    with c3:
        control_widget(col)
    H('<div class="rowhr"></div>')


def page_assessment():
    header("Security Assessment", "A control-based questionnaire. Answer each control as it applies today; the score on this page updates live.")
    record = read_record()
    score, tier = P.predict(record)
    rows = I.register_rows(record, {})
    good = sum(1 for r in rows if r["cls"] == "good")
    gaps = sum(1 for r in rows if r["cls"] == "bad")
    k = st.columns(4)
    k[0].markdown(kpi("Live risk score", f"{score:g}", "out of 100, updates as you answer", TIER_COLOR[tier]), unsafe_allow_html=True)
    k[1].markdown(kpi("Risk tier", f'<span class="badge" style="background:{TIER_COLOR[tier]}">{tier.upper()}</span>', "from the ML classifier", TIER_COLOR[tier]), unsafe_allow_html=True)
    k[2].markdown(kpi("Controls implemented", f"{good} <span style='font-size:1rem;color:#667085'>/ {len(rows)}</span>", "satisfactory responses", "#15803D"), unsafe_allow_html=True)
    k[3].markdown(kpi("Open gaps", f"{gaps}", "controls not in place", "#DC2626"), unsafe_allow_html=True)
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">Assessment details</div><div class="cards">These details appear on the generated report.</div>')
        a, b, c = st.columns(3)
        a.text_input("Organisation name", key="meta_org", placeholder="e.g. Acme Retail Pvt Ltd")
        b.text_input("Assessor / contact", key="meta_assessor", placeholder="e.g. Het Patel")
        c.text_input("Scope", key="meta_scope")
    with st.expander("AI-assisted intake: describe the organisation and pre-fill the questionnaire", expanded=False):
        st.text_area("Description", key="desc", height=100, label_visibility="collapsed",
                     placeholder="Example: We are a retail business with 25 employees. We do not use MFA, our Windows PCs are outdated and backups run once a month.")
        st.button("Pre-fill questionnaire from description", on_click=autofill)
        if st.session_state.get("autofill_msg"):
            st.success(st.session_state["autofill_msg"])
    st.write("")
    try:
        box = st.container(key="assess")
    except TypeError:
        box = st.container()
    with box:
        tabs = st.tabs([f"{code} · {SHORT[code]}" for code, *_ in I.DOMAINS])
        for tab, (code, name, desc, cols) in zip(tabs, I.DOMAINS):
            with tab:
                cols = [c for c in cols if c in P.COLUMNS]
                H(f'<div class="dhead"><div class="dcode">{code}</div><div><div class="dname">{esc(name)}</div><div class="ddesc">{esc(desc)}</div></div></div>'
                  '<div class="thead"><div style="flex:5.6">Control and guidance</div><div style="flex:2.3">Framework reference</div><div style="flex:2.6">Response</div></div>')
                for c in cols:
                    control_row(c)
    st.write("")
    if st.button("Run risk assessment", type="primary"):
        with st.spinner("Scoring responses, computing SHAP explanations and writing the analysis..."):
            record = read_record()
            sc, tr = P.predict(record)
            impacts = P.explain_all(record)
            ins = I.build_insights(record, sc, tr, impacts, meta() | {"name": meta()["org"] if st.session_state["meta_org"].strip() else ""}, st.session_state["use_llm"])
            for k_ in [k_ for k_ in st.session_state if k_.startswith("fix_")]:
                del st.session_state[k_]
            for n, it in enumerate(ins["items"]):
                st.session_state[f"fix_{it['col']}"] = it["effort"] == "Low"
            st.session_state["res"] = dict(record=record, score=sc, tier=tr, impacts=impacts, when=datetime.now().strftime("%d %B %Y, %H:%M"))
            st.session_state["ins"] = ins
        st.session_state["_goto"] = "Dashboard"
        st.rerun()


# =============================================================== page: dashboard
def drivers_html(ins, n=6):
    top = max([d["points"] for d in ins["drivers"]] or [1])
    return "".join(f'<div class="row"><div class="rank">{i}</div><div class="t">{esc(d["title"])}<small>{d["id"]} · current: {esc(d["value"])}</small></div>'
                   f'<div style="width:90px"><div class="bar"><i style="width:{d["points"] / top * 100:.0f}%;background:#DC2626"></i></div></div><div class="v">+{d["points"]:g}</div></div>'
                   for i, d in enumerate(ins["drivers"][:n], 1))


def page_dashboard():
    if not need_results():
        return
    res, ins = st.session_state["res"], st.session_state["ins"]
    score, tier = res["score"], res["tier"]
    color = TIER_COLOR[tier]
    header("Executive Dashboard", f"Assessment completed {res['when']}. Overall posture, main drivers and the projected effect of remediation.")
    reg = ins["register"]
    good = sum(1 for r in reg if r["cls"] == "good")
    k = st.columns(4)
    k[0].markdown(kpi("Overall risk score", f"{score:g}", "out of 100 (higher = more risk)", color), unsafe_allow_html=True)
    k[1].markdown(kpi("Risk tier", f'<span class="badge" style="background:{color}">{tier.upper()}</span>', f"average organisation: {ins['waterfall']['base']:.0f}", color), unsafe_allow_html=True)
    k[2].markdown(kpi("Control coverage", f"{round(100 * good / len(reg))}%", f"{good} of {len(reg)} controls satisfactory", "#15803D"), unsafe_allow_html=True)
    k[3].markdown(kpi("Projected score", f"{ins['projected']:g}", "after the 90-day roadmap", "#2563EB"), unsafe_allow_html=True)
    st.write("")
    a, b, c = st.columns([1, 1.25, 1.35])
    with a:
        with st.container(border=True):
            H('<div class="cardh">Risk meter</div><div class="cards">Position on the 0-100 scale</div>')
            H(f'<div style="text-align:center">{I.gauge_svg(score, 290)}<div style="margin-top:2px"><span class="badge" style="background:{color}">{tier.upper()} RISK</span></div></div>')
    with b:
        with st.container(border=True):
            H('<div class="cardh">Risk by domain</div><div class="cards">Net points each domain adds (red) or removes (green)</div>')
            top = max(abs(d["net"]) for d in ins["domains"]) or 1
            H("".join(f'<div class="dom"><div class="lab"><span>{d["code"]} · {esc(d["name"])}</span><span>{d["net"]:+.1f}</span></div>'
                      f'<div class="bar"><i style="width:{max(3, abs(d["net"]) / top * 100):.0f}%;background:{"#DC2626" if d["net"] > 0 else "#15803D"}"></i></div></div>'
                      for d in sorted(ins["domains"], key=lambda d: -d["net"])))
    with c:
        with st.container(border=True):
            H('<div class="cardh">Top risk drivers</div><div class="cards">Largest contributors to the score (SHAP)</div>')
            H(drivers_html(ins))
    st.write("")
    a, b = st.columns([1.5, 1])
    with a:
        with st.container(border=True):
            H(f'<div class="cardh">Executive summary<span class="src">{esc(ins["source"])}</span></div>')
            H(f'<div class="lead">{esc(ins["executive_summary"])}</div>')
            st.caption("See the Score Explanation page for the full breakdown.")
    with b:
        with st.container(border=True):
            H('<div class="cardh">Projected risk reduction</div><div class="cards">Score after each remediation phase</div>')
            parts = f'<div class="step"><div class="l">Today</div><div class="v">{score:g}</div><div class="w">now</div></div>'
            for ph in ins["phases"]:
                parts += f'<div class="arrow">›</div><div class="step"><div class="l">{ph["name"]}</div><div class="v" style="color:#15803D">{ph["after"]:g}</div><div class="w">{ph["window"]}</div></div>'
            H(f'<div class="steps">{parts}</div>')
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">Domain scorecard</div><div class="cards">Control status per domain</div>')
        rows = "".join(
            f'<tr><td><b>{d["code"]}</b></td><td>{esc(d["name"])}</td><td><span class="st good">{d["good"]} OK</span> <span class="st mid">{d["mid"]} partial</span> '
            f'<span class="st bad">{d["bad"]} gaps</span></td><td>{d["net"]:+.1f}</td>'
            f'<td><span class="st {"bad" if d["net"] > 3 else "mid" if d["net"] > 0.5 else "good"}">{"High" if d["net"] > 3 else "Medium" if d["net"] > 0.5 else "Low"}</span></td></tr>'
            for d in sorted(ins["domains"], key=lambda d: -d["net"]))
        H(f'<table class="t"><tr><th>Code</th><th>Domain</th><th>Controls</th><th>Net risk points</th><th>Priority</th></tr>{rows}</table>')


# =============================================================== page: score explanation
def waterfall_html(ins, score):
    base, bars = I.waterfall_geometry(ins)
    rows = ""
    for b in bars:
        color = "#98A2B3" if b["delta"] is None else "#DC2626" if b["delta"] > 0 else "#15803D"
        points = f"{base:.1f}" if b["delta"] is None else f"{b['delta']:+.1f}"
        rows += (f'<tr><td>{esc(b["label"])}</td><td style="width:50%"><div class="wf"><i style="left:{max(0, b["left"]):.1f}%;'
                 f'width:{b["width"]:.1f}%;background:{color}"></i></div></td><td><b style="color:{color}">{points}</b></td></tr>')
    rows += f'<tr><td><b>Final risk score</b></td><td></td><td><b>{score:g}</b></td></tr>'
    return f'<table class="t"><tr><th>Factor</th><th>Contribution on the 0-100 scale</th><th>Points</th></tr>{rows}</table>'


def page_explain():
    if not need_results():
        return
    res, ins = st.session_state["res"], st.session_state["ins"]
    score, tier = res["score"], res["tier"]
    color = TIER_COLOR[tier]
    header("Score Explanation", "A detailed, plain-language explanation of why the organisation received this score.")
    with st.container(border=True):
        H(f'<div class="cardh">1. Executive summary<span class="src">{esc(ins["source"])}</span></div><div class="cards">Written for management</div>')
        H(f'<div class="lead">{esc(ins["executive_summary"])}</div>')
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">2. What this score means</div><div class="cards">Risk tiers on the 0-100 scale</div>')
        H(f'<div class="scale"><span style="background:#15803D"></span><span style="background:#EAB308"></span><span style="background:#EA580C"></span><span style="background:#DC2626"></span>'
          f'<div class="mark" style="left:calc({min(99, max(0, score)):.0f}% - 2px)"></div></div>'
          '<div class="scalelab"><span>0 · Low</span><span>25 · Medium</span><span>50 · High</span><span>75 · Critical</span><span>100</span></div>')
        H(f'<p class="lead" style="margin-top:14px"><span class="badge" style="background:{color}">{tier.upper()}</span> &nbsp;{esc(ins["meaning"])}</p>')
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">3. How the score was calculated</div><div class="cards">SHAP breakdown: the model starts at the average organisation and adds or removes points for each answer</div>')
        H(waterfall_html(ins, score))
        H('<div class="note">Red bars are answers that raise the risk score; green bars are answers that lower it. The contributions add up exactly to the final score.</div>')
    st.write("")
    with st.container(border=True):
        H(f'<div class="cardh">4. Risk driver analysis<span class="src">{esc(ins["source"])}</span></div><div class="cards">Open each driver for the full explanation</div>')
        for i, d in enumerate(ins["drivers"][:8]):
            with st.expander(f"{i + 1}.  {d['title']}  ({d['id']})  ·  current: {d['value']}  ·  +{d['points']:g} points", expanded=i == 0):
                H(f'<div class="dd"><b>Assessment</b><div>{esc(d["insight"])}</div><b>Why it matters</b><div>{esc(d["why"])}</div>'
                  f'<b>Business impact</b><div>{esc(d["impact"])}</div><b>Recommended action</b><div>{esc(d["fix"])}</div>'
                  f'<b>Effort / cost</b><div>{d["effort"]} effort · {d["cost"]} cost · typically {dict(Low="0-30", Medium="30-60", High="60-90").get(d["effort"], "")} days</div>'
                  f'<b>Framework</b><div>{esc(d["refs"])}</div></div>')
    st.write("")
    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            H('<div class="cardh">5. What is working well</div><div class="cards">Controls that are lowering the score</div>')
            if ins["strengths"]:
                H("".join(f'<div class="row"><div class="rank" style="background:#DCFCE7;color:#166534">✓</div><div class="t">{esc(s["title"])}<small>current: {esc(s["value"])}</small></div>'
                          f'<div class="v" style="color:#15803D">{s["points"]:+g}</div></div>' for s in ins["strengths"]))
            else:
                st.info("No control is strongly reducing the score yet.")
    with b:
        with st.container(border=True):
            H('<div class="cardh">6. Domain commentary</div><div class="cards">Where the gaps sit</div>')
            lines = ""
            for d in sorted(ins["domains"], key=lambda d: -d["net"]):
                bad = [r["control"] for r in ins["register"] if r["domain"] == d["name"] and r["cls"] == "bad"]
                lines += (f'<div class="row"><div class="t">{d["code"]} · {esc(d["name"])}<small>{d["good"]} of {d["total"]} controls satisfactory'
                          f'{" · gaps: " + esc(", ".join(bad)) if bad else ""}</small></div><div class="v" style="color:{"#DC2626" if d["net"] > 0 else "#15803D"}">{d["net"]:+.1f}</div></div>')
            H(lines)
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">7. Outlook</div>')
        H(f'<div class="lead">{esc(ins["outlook"])}</div>')


# =============================================================== page: remediation
def page_remediation():
    if not need_results():
        return
    res, ins = st.session_state["res"], st.session_state["ins"]
    score, record = res["score"], res["record"]
    header("Remediation Roadmap", "Prioritised actions grouped by effort, with the modelled score reduction for each phase.")
    ph = ins["phases"]
    k = st.columns(4)
    k[0].markdown(kpi("Current score", f"{score:g}", res["tier"] + " risk", TIER_COLOR[res["tier"]]), unsafe_allow_html=True)
    for i, p_ in enumerate(ph):
        k[i + 1].markdown(kpi(f"After {p_['name'].lower()}", f"{p_['after']:g}", f"{p_['window']} · {len(p_['items'])} actions", "#15803D"), unsafe_allow_html=True)
    st.write("")
    for p_ in ph:
        if not p_["items"]:
            continue
        with st.container(border=True):
            H(f'<div class="cardh">{p_["name"]} <span style="color:#667085;font-weight:500">· {p_["window"]} · {p_["effort"]} effort</span><span class="src">{p_["before"]:g} → {p_["after"]:g}</span></div><div class="cards">&nbsp;</div>')
            rows = "".join(f'<tr><td><b>{esc(i["title"])}</b> <small>({i["id"]})</small><br><small>{esc(i["note"])}</small></td><td>{esc(i["frm"])} → <b>{esc(i["to"])}</b></td>'
                           f'<td>{i["effort"]} / {i["cost"]}</td><td style="color:#15803D"><b>-{i["drop"]:g}</b></td><td><small>{esc(i["refs"])}</small></td></tr>' for i in p_["items"])
            H(f'<table class="t"><tr><th>Action</th><th>Change</th><th>Effort / cost</th><th>Est. reduction</th><th>Framework</th></tr>{rows}</table>')
        st.write("")
    with st.container(border=True):
        H('<div class="cardh">What-if simulator</div><div class="cards">Select the actions you plan to complete. The model recalculates the score instantly.</div>')
        if ins["items"]:
            chosen = {}
            cc = st.columns(2)
            for n, it in enumerate(sorted(ins["items"], key=lambda i: -i["drop"])):
                with cc[n % 2]:
                    if st.checkbox(f"{it['title']}: {it['frm']} → {it['to']}  (−{it['drop']:g})", key=f"fix_{it['col']}"):
                        chosen[it["col"]] = it["to"]
            ns, nt = P.predict({**record, **chosen})
            H(f'<div class="steps" style="margin-top:12px"><div class="step"><div class="l">Current</div><div class="v">{score:g}</div><div class="w">{res["tier"]}</div></div>'
              f'<div class="arrow">›</div><div class="step"><div class="l">After selected actions</div><div class="v" style="color:#15803D">{ns:g}</div><div class="w">{nt}</div></div>'
              f'<div class="step"><div class="l">Reduction</div><div class="v" style="color:#15803D">{max(0, score - ns):.1f}</div><div class="w">points</div></div></div>')
        else:
            st.info("No actionable improvements were found.")


# =============================================================== page: reports
def page_reports():
    if not need_results():
        return
    res, ins = st.session_state["res"], st.session_state["ins"]
    header("Reports & Exports", "Download the executive report and the underlying data.")
    m = meta()
    report = I.report_html(m, res, ins)
    a, b, c = st.columns(3)
    with a:
        with st.container(border=True):
            H('<div class="cardh">Executive report</div><div class="cards">Print-ready HTML with summary, SHAP breakdown, roadmap and control register. Use Print → Save as PDF.</div>')
            st.download_button("Download report (HTML)", report, file_name=f"RakshaScore_Report_{m['ref']}.html", mime="text/html", **STRETCH)
    with b:
        with st.container(border=True):
            H('<div class="cardh">Control register</div><div class="cards">All controls with response, status, risk contribution and framework references.</div>')
            st.download_button("Download register (CSV)", I.register_csv(ins["register"]), file_name=f"RakshaScore_Register_{m['ref']}.csv", mime="text/csv", **STRETCH)
    with c:
        with st.container(border=True):
            H('<div class="cardh">Assessment data</div><div class="cards">Raw responses and results in JSON for audit trails or integration.</div>')
            payload = json.dumps(dict(meta=m, score=res["score"], tier=res["tier"], responses=res["record"], generated=res["when"]), indent=2, default=str)
            st.download_button("Download data (JSON)", payload, file_name=f"RakshaScore_Data_{m['ref']}.json", mime="application/json", **STRETCH)
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">Report preview</div><div class="cards">This is exactly what the downloaded file looks like.</div>')
        components.html(report, height=900, scrolling=True)


# =============================================================== page: methodology
def page_method():
    header("Methodology", "How the assessment works and how well the models perform.")
    with st.container(border=True):
        H('<div class="cardh">Assessment pipeline</div><div class="cards">From responses to an explained, prioritised plan</div>')
        steps = [("1. Intake", "Responses are collected through a control-based questionnaire. Optionally an LLM reads a free-text description and pre-fills the answers; it never decides the score."),
                 ("2. Scoring", "A gradient-boosted tree model predicts a 0-100 risk score and a risk tier (Low, Medium, High, Critical) from the structured answers."),
                 ("3. Explanation", "SHAP attributes the score to individual answers, starting from the average organisation. An LLM (or offline templates) turns this into a plain-language narrative grounded in a control knowledge base."),
                 ("4. Remediation", "Each gap is re-scored by changing the answer and re-running the model, which gives the real modelled reduction. Actions are grouped by effort into 30/60/90-day phases.")]
        H('<table class="t">' + "".join(f"<tr><td style='width:160px'><b>{t}</b></td><td>{d}</td></tr>" for t, d in steps) + "</table>")
    res_dir = RESULTS_DIR
    comp = res_dir / "model_comparison.csv"
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">Model performance</div><div class="cards">Held-out test set, produced by scripts/train_models.py</div>')
        if comp.exists():
            st.dataframe(pd.read_csv(comp), hide_index=True, **STRETCH)
            for f, t in [("score_model_metrics.txt", "Risk-score regressor"), ("cross_validation.txt", "Cross-validation")]:
                fp = res_dir / f
                if fp.exists():
                    st.caption(f"{t}: " + fp.read_text().strip().replace("\n", " | "))
        else:
            H('<div class="note">Run <b>python scripts/train_models.py</b> to populate the model results.</div>')
    imgs = [(f, t) for f, t in [("confusion_matrix.png", "Confusion matrix"), ("shap_summary.png", "SHAP feature impact")] if (res_dir / f).exists()]
    if imgs:
        st.write("")
        for col_, (f, t) in zip(st.columns(len(imgs)), imgs):
            with col_:
                with st.container(border=True):
                    H(f'<div class="cardh">{t}</div>')
                    st.image(res_dir / f)
    st.write("")
    with st.container(border=True):
        H('<div class="cardh">Assumptions and limitations</div>')
        H('<div class="note"><b>Synthetic training data.</b> No public labelled dataset of small-business breaches exists, so the model was trained on data generated from published statistics. '
          'High accuracy shows the model learned the scoring logic, not real-world predictive power; validation on real assessments is future work.</div>'
          '<div class="note"><b>Self-reported answers.</b> Responses are not independently verified. <b>Framework mapping.</b> CIS Controls v8, ISO/IEC 27001:2022 and NIST CSF references are indicative '
          'and do not constitute a compliance assessment. This tool supports, but does not replace, a professional security audit.</div>')


{"Assessment": page_assessment, "Dashboard": page_dashboard, "Score Explanation": page_explain, "Remediation": page_remediation,
 "Reports": page_reports, "Methodology": page_method}[view]()
