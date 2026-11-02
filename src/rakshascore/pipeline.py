"""
RakshaScore core pipeline
  text -> extract_factors (LLM, or rule-based fallback) -> build_record (fill defaults)
       -> predict (risk tier + 0-100 score) -> explain (SHAP) -> recommend (LLM, or template fallback)
"""
import json, os, re
import joblib
import numpy as np
import pandas as pd
import shap
from dotenv import load_dotenv

from . import paths

load_dotenv(paths.ENV_PATH, override=False)        # optional .env at the repository root
LAST_ERROR = ""                                    # last LLM problem, so the app can show it


def _key(name):
    """Read a key from the environment and remove stray spaces, quotes and <> brackets."""
    return os.getenv(name, "").strip().strip('"').strip("'").strip("<>").strip()
SCHEMA = json.loads(paths.SCHEMA_PATH.read_text(encoding="utf-8"))
COLUMNS = SCHEMA["columns"]
CAT, NUM = SCHEMA["categorical"], SCHEMA["numeric"]

CLF = joblib.load(paths.CLF_PATH)                  # saved XGBoost pipeline
LE = joblib.load(paths.LABEL_ENCODER_PATH)
REG = joblib.load(paths.SCORE_MODEL_PATH)

LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")                  # Anthropic model
GEMINI_MODELS = [m for m in [os.getenv("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"] if m]
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
HIGHER_IS_RISKIER = SCHEMA.get("score_higher_is_riskier", True)
SIGN = 1.0 if HIGHER_IS_RISKIER else -1.0          # makes every number below mean "higher = more risk"


# ---------------------------------------------------------------- LLM helper (Anthropic / Gemini free / Ollama local)
def _provider_ready(name):
    if name == "anthropic":
        return bool(_key("ANTHROPIC_API_KEY"))
    if name == "gemini":
        return bool(_key("GEMINI_API_KEY") or _key("GOOGLE_API_KEY"))
    if name == "ollama":
        return True                                   # only used when you ask for it (LLM_PROVIDER=ollama)
    return False


def llm_provider():
    """Which LLM will be used: 'anthropic', 'gemini', 'ollama' or None (-> offline rule-based fallback)."""
    forced = os.getenv("LLM_PROVIDER", "").strip().lower()
    if forced:
        return forced if _provider_ready(forced) else None
    for name in ("anthropic", "gemini"):
        if _provider_ready(name):
            return name
    return None


def llm_available():
    return llm_provider() is not None


def set_provider_key(name, key):
    """Called by the app when the user pastes a key into the sidebar (lives only while the app is running)."""
    var = "GEMINI_API_KEY" if name == "gemini" else "ANTHROPIC_API_KEY"
    os.environ[var] = key.strip().strip('"').strip("'").strip("<>").strip()
    os.environ["LLM_PROVIDER"] = name


def test_llm():
    """Tiny real call. Returns (ok, message) - message contains the real error if something is wrong."""
    prov = llm_provider()
    if not prov:
        return False, "No API key found. Paste your key in the box above (or create a .env file)."
    try:
        out = call_llm("Reply with exactly the word: OK", "ping", max_tokens=20)
        return True, f"Connected to {prov}. Model replied: {out.strip()[:40]}"
    except Exception as e:
        return False, f"{prov} problem: {str(e)[:350]}"


def _call_gemini(system, user, max_tokens):
    import requests
    key = _key("GEMINI_API_KEY") or _key("GOOGLE_API_KEY")
    last_err = None
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        gen = {"maxOutputTokens": max_tokens + 1024, "temperature": 0, "thinkingConfig": {"thinkingBudget": 0}}
        body = {"system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": gen}
        for attempt in range(2):
            r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=60)
            if r.status_code == 400 and attempt == 0 and "thinking" in r.text.lower():
                gen.pop("thinkingConfig", None)            # this model does not accept thinkingConfig - retry without it
                continue
            break
        if r.status_code == 200:
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(x.get("text", "") for x in parts)
        last_err = f"Gemini {model}: HTTP {r.status_code} {r.text[:200]}"
        if r.status_code not in (400, 404):                # 429 / 403 etc. -> trying another model will not help
            break
    raise RuntimeError(last_err)


def _call_ollama(system, user, max_tokens):
    import requests
    r = requests.post("http://localhost:11434/api/chat", timeout=180, json={
        "model": OLLAMA_MODEL, "stream": False, "options": {"temperature": 0, "num_predict": max_tokens},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["message"]["content"]


def call_llm(system, user, max_tokens=600):
    """Single place that talks to the LLM. Provider is chosen by llm_provider()."""
    prov = llm_provider()
    if prov == "gemini":
        return _call_gemini(system, user, max_tokens)
    if prov == "ollama":
        return _call_ollama(system, user, max_tokens)
    if prov == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=_key("ANTHROPIC_API_KEY"))
        resp = client.messages.create(model=LLM_MODEL, max_tokens=max_tokens, system=system,
                                      messages=[{"role": "user", "content": user}])
        return resp.content[0].text
    raise RuntimeError("No LLM configured")


# ---------------------------------------------------------------- 1. extraction
def _schema_prompt():
    lines = [f"- {c}: one of {v['values']}" for c, v in CAT.items()]
    lines += [f"- {c}: a number between {v['min']:.0f} and {v['max']:.0f}" for c, v in NUM.items()]
    return "\n".join(lines)


EXTRACT_SYSTEM = """You extract cybersecurity facts from a description of a small business.
Return ONLY a JSON object. Use only these field names and allowed values:
{schema}
Rules: include a field ONLY if the text clearly states or strongly implies it. Never guess.
Omit everything else. No explanations, no markdown."""


def _llm_extract(text):
    raw = call_llm(EXTRACT_SYSTEM.format(schema=_schema_prompt()), text, max_tokens=800)
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


NEG = r"(?:no|not|without|doesn'?t|does not|don'?t|do not|lack|lacks|missing|never)\W+(?:\w+\W+){0,3}?"
YESNO_KEYWORDS = {
    "mfa_enabled": r"mfa|multi.?factor|2fa|two.?factor",
    "firewall_enabled": r"firewall",
    "antivirus_enabled": r"anti.?virus",
    "edr_enabled": r"\bedr\b",
    "vpn_enabled": r"\bvpn\b",
    "siem_enabled": r"siem",
    "device_encryption": r"device encryption|disk encryption|encrypt\w* (?:laptops|devices|disks)",
    "data_encryption": r"data encryption|encrypt\w* (?:data|databases?)",
    "incident_response_plan": r"incident response",
    "security_policy": r"security policy",
    "phishing_training": r"phishing",
    "vulnerability_scanning": r"vulnerability scan\w*",
}


def _pick(field, preferred):
    """Return the first preferred label that really exists for this column, else None."""
    allowed = {v.lower(): v for v in CAT.get(field, {}).get("values", [])}
    for p in preferred:
        if p.lower() in allowed:
            return allowed[p.lower()]
    return None


def _rule_extract(text):
    """Offline fallback (no API key / no internet). Simple keyword rules - fewer fields than the LLM."""
    t = text.lower()
    out = {}
    for field, kw in YESNO_KEYWORDS.items():
        if field not in CAT:
            continue
        if re.search(NEG + f"(?:{kw})", t):
            out[field] = _pick(field, ["No"])
        elif re.search(kw, t):
            out[field] = _pick(field, ["Yes"])
    # backups
    if "backup_frequency" in CAT:
        if re.search(NEG + r"backups?", t):
            out["backup_enabled"] = _pick("backup_enabled", ["No"])
            out["backup_frequency"] = _pick("backup_frequency", ["Unknown", "Never"])
        else:
            for word, label in [("daily", "Daily"), ("weekly", "Weekly"), ("month", "Monthly"),
                                ("quarter", "Quarterly"), ("year|annual", "Yearly")]:
                if re.search(rf"backups?[^.]*?(?:{word})|(?:{word})\w*[^.]*?backups?", t):
                    out["backup_frequency"] = _pick("backup_frequency", [label])
                    out["backup_enabled"] = _pick("backup_enabled", ["Yes"])
                    break
    # patching
    if re.search(r"outdated|unpatched|not patched|old (?:windows|software|systems)|end.of.life", t):
        out["patch_management"] = _pick("patch_management", ["Poor", "Weak", "Low", "No"])
    elif re.search(r"up.to.date|regularly patched|automatic updates|patched (?:monthly|weekly)", t):
        out["patch_management"] = _pick("patch_management", ["Good", "Strong", "High", "Yes"])
    # training
    if re.search(NEG + r"(?:security |cyber )?(?:awareness )?training", t):
        out["security_training"] = _pick("security_training", ["No", "None", "Never", "Poor"])
    elif re.search(r"(?:security|cyber)[^.]*training|trained", t):
        out["security_training"] = _pick("security_training", ["Yes", "Regular", "Good"])
    # employee count
    m = re.search(r"(\d+)\s+(?:employees|staff|people|workers)", t)
    if m and "employee_count" in NUM:
        out["employee_count"] = int(m.group(1))
    return {k: v for k, v in out.items() if v is not None}


def _validate(found):
    """Keep only fields that exist AND whose value is allowed. Stops the LLM inventing categories."""
    clean = {}
    for k, v in found.items():
        if k in CAT:
            match = {a.lower(): a for a in CAT[k]["values"]}.get(str(v).strip().lower())
            if match:
                clean[k] = match
        elif k in NUM:
            try:
                clean[k] = float(np.clip(float(v), NUM[k]["min"], NUM[k]["max"]))
            except (TypeError, ValueError):
                pass
    return clean


def extract_factors(text, use_llm=True):
    """Returns (validated_fields, method_used)."""
    global LAST_ERROR
    LAST_ERROR = ""
    if use_llm and llm_available():
        for _ in range(2):                       # one retry if the JSON comes back broken
            try:
                found = _validate(_llm_extract(text))
                if found:
                    return found, f"LLM ({llm_provider()})"
            except Exception as e:
                LAST_ERROR = str(e)[:250]
                print("LLM extraction failed:", e)
    return _validate(_rule_extract(text)), "rule-based fallback"


def build_record(found):
    """Fill every column the text didn't mention with the dataset default; remember which were assumed."""
    record, assumed = {}, []
    for c in COLUMNS:
        if c in found:
            record[c] = found[c]
        else:
            record[c] = CAT[c]["default"] if c in CAT else NUM[c]["default"]
            assumed.append(c)
    return record, assumed


# ---------------------------------------------------------------- 2. prediction
def _frame(record):
    return pd.DataFrame([record])[COLUMNS]


def predict(record):
    X = _frame(record)
    tier = str(LE.inverse_transform(CLF.predict(X))[0])
    return risk_score(record), tier


def risk_scores(records):
    """Score many records in a single model call (same semantics as risk_score, ~100x faster)."""
    raw = np.clip(REG.predict(pd.DataFrame(list(records))[COLUMNS]), 0, 100)
    return [round(float(r) if HIGHER_IS_RISKIER else 100 - float(r), 1) for r in raw]


def risk_score(record):
    """0-100 where HIGHER ALWAYS MEANS MORE RISK (flips automatically if your dataset is the other way round)."""
    return risk_scores([record])[0]


# ---------------------------------------------------------------- 3. SHAP
_PRE = REG.named_steps["preprocessor"]
_REGR = REG.named_steps["regressor"]
_NAMES = list(_PRE.get_feature_names_out())
_EXPLAINER = shap.TreeExplainer(_REGR)


def _origin(feature_name):
    """'cat__mfa_enabled_No' -> 'mfa_enabled' (merge one-hot columns back into the original question)."""
    body = feature_name.split("__", 1)[1]
    for c in sorted(COLUMNS, key=len, reverse=True):
        if body == c or body.startswith(c + "_"):
            return c
    return body


def base_value():
    """Average-organisation risk score the model starts from (SHAP baseline), in 'higher = more risk' terms."""
    ev = float(np.ravel(_EXPLAINER.expected_value)[0])
    return ev if HIGHER_IS_RISKIER else 100 - ev


def explain_all(record):
    """SHAP impact (in score points) of EVERY question. Positive = pushes risk UP."""
    Xt = _PRE.transform(_frame(record))
    Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
    sv = _EXPLAINER.shap_values(Xt)[0] * SIGN
    agg = {}
    for name, v in zip(_NAMES, sv):
        col = _origin(name)
        agg[col] = agg.get(col, 0.0) + float(v)
    return agg


def explain(record, top_k=5):
    """Top risk-raising factors as (column, value, impact)."""
    ranked = sorted(explain_all(record).items(), key=lambda kv: -kv[1])
    return [(c, record[c], round(v, 2)) for c, v in ranked[:top_k] if v > 0]


# Things a business cannot "fix" with an action (used by the what-if simulator)
NOT_FIXABLE = {"company_size", "industry", "annual_revenue", "employee_count",
               "previous_incidents", "incident_count_last_year"}


def best_fix(record, col, base=None):
    """Try every allowed value for one question; return (best_value, new_score)."""
    base = risk_score(record) if base is None else base
    options = CAT[col]["values"] if col in CAT else [NUM[col]["min"]]
    trials = []
    for value in options:
        trial = dict(record)
        trial[col] = value
        trials.append(trial)
    scores = risk_scores(trials)
    i = min(range(len(options)), key=lambda k: scores[k])
    return (options[i], scores[i]) if scores[i] < base else (record[col], base)


def fix_plan(record, top_k=6):
    """The questions where changing the answer lowers the score most. Returns list of dicts."""
    base = risk_score(record)
    ranked = [(c, v) for c, v in sorted(explain_all(record).items(), key=lambda kv: -kv[1])
              if v > 0 and c not in NOT_FIXABLE]
    if not ranked:
        return []

    # Score every candidate value for every driver in ONE model call.
    options = {c: (CAT[c]["values"] if c in CAT else [NUM[c]["min"]]) for c, _ in ranked}
    trials, spans = [], []
    for col, _ in ranked:
        start = len(trials)
        for value in options[col]:
            trial = dict(record)
            trial[col] = value
            trials.append(trial)
        spans.append((col, start, len(trials)))

    scores = risk_scores(trials)
    plan = []
    for col, start, end in spans:
        segment = scores[start:end]
        i = min(range(len(segment)), key=lambda k: segment[k])
        if segment[i] < base - 0.05:
            plan.append({"column": col, "from": record[col], "to": options[col][i],
                         "drop": round(base - segment[i], 1)})
        if len(plan) == top_k:
            break
    return plan


# ---------------------------------------------------------------- 4. recommendations
FIXES = {
    "mfa_enabled": "Turn on multi-factor authentication for email, admin and cloud accounts (free in Google/Microsoft).",
    "patch_management": "Enable automatic updates and patch critical vulnerabilities within 30 days.",
    "backup_enabled": "Set up automated backups to an offline or cloud location.",
    "backup_frequency": "Move to daily or weekly backups.",
    "backup_tested": "Test a backup restore at least twice a year.",
    "security_training": "Run a short security-awareness session every quarter.",
    "phishing_training": "Run quarterly phishing-awareness drills.",
    "incident_response_plan": "Write a one-page incident response plan with named contacts.",
    "security_policy": "Adopt a basic written security policy using a free CIS-based template.",
    "firewall_enabled": "Enable a business firewall on the network edge.",
    "antivirus_enabled": "Install endpoint antivirus on every business device.",
    "edr_enabled": "Add endpoint detection and response on critical machines.",
    "device_encryption": "Turn on full-disk encryption (BitLocker/FileVault) on laptops.",
    "data_encryption": "Encrypt sensitive data at rest and in transit.",
    "asset_inventory": "Keep a simple inventory of all devices and software.",
    "critical_vulnerabilities": "Fix or isolate systems with known critical vulnerabilities.",
    "password_policy": "Enforce a strong password policy with a password manager.",
    "network_segmentation": "Separate guest/IoT devices from the business network.",
    "vulnerability_scanning": "Schedule a monthly vulnerability scan.",
    "security_monitoring": "Turn on alerts for logins and admin changes.",
}

REC_SYSTEM = """You are a cybersecurity advisor for non-technical small business owners.
Write exactly 3 prioritised actions, one sentence each, cheapest effective fix first.
Only address the risk factors given. Do not invent other risks. Plain language, no jargon.
Factors marked (assumed) were NOT stated by the owner - phrase those as "check whether ..." instead of stating a fact."""


def recommend(score, tier, factors, assumed=()):
    if not factors:
        return ["No major risk drivers found. Keep your current practices and review them every quarter."], "template"
    if llm_available():
        try:
            facts = "; ".join(f"{c} = {v}{' (assumed)' if c in assumed else ''} (adds {i} points)" for c, v, i in factors)
            prompt = f"Risk score {score}/100, level {tier}.\nTop risk drivers, highest first: {facts}"
            lines = [re.sub(r"^[\s\-\*\d\.\)]+", "", l).strip() for l in call_llm(REC_SYSTEM, prompt, 400).splitlines() if l.strip()]
            if lines:
                return lines[:3], f"LLM ({llm_provider()})"
        except Exception as e:
            print("LLM recommendation failed:", e)
    out = []
    for c, v, i in factors[:3]:
        fix = FIXES.get(c, f"Review your '{c.replace('_', ' ')}' setup (currently: {v}) - it adds {i} points to your risk score.")
        out.append(("If not already in place: " + fix[0].lower() + fix[1:]) if c in assumed else fix)
    return out, "template fallback"
