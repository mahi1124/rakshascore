"""
insights.py - control knowledge base, score explanation (AI or offline) and the enterprise HTML report.
Used by app_enterprise.py. Everything the AI says is grounded in the facts and KB text below.
"""
import csv
import html as _h
import io
import json
import math
from datetime import datetime

from . import pipeline as P

# --------------------------------------------------------------------------------------------- knowledge base
# col: (id, title, question, guidance, refs, why, impact, fix, effort, cost)
KB = {
    "mfa_enabled": ("IAM-01", "Multi-factor authentication",
        "Is multi-factor authentication (MFA) enforced for email, remote access and administrator accounts?",
        "Answer Yes only if MFA is enforced, not merely available. Authenticator apps or hardware keys are preferred over SMS.",
        "CIS 6.3-6.5 · ISO 27001 A.8.5 · NIST CSF PR.AA",
        "MFA stops most credential-theft attacks, because a stolen password alone is no longer enough to log in.",
        "Without MFA, one phished or reused password can give attackers full access to email, cloud files and finance systems.",
        "Enforce MFA on email, remote access and all admin accounts first, using an authenticator app (free in Microsoft 365 and Google Workspace).",
        "Low", "Free"),
    "password_policy": ("IAM-02", "Password policy strength",
        "How strong is the enforced password policy?",
        "Strong: 12+ characters, no reuse, password manager in use. Moderate: minimum length and complexity enforced. Weak: no enforced rules.",
        "CIS 5.2 · ISO 27001 A.5.17",
        "Weak and reused passwords are the easiest way into accounts through guessing and credential stuffing.",
        "Attackers can reuse passwords leaked from other sites to break into business accounts at scale.",
        "Set a 12+ character minimum, block common passwords and roll out a business password manager.",
        "Low", "Low"),
    "privileged_accounts": ("IAM-03", "Privileged (admin) accounts",
        "How many accounts hold administrator or privileged access?",
        "Count every account that can change systems, install software or reach all data. Fewer is safer.",
        "CIS 5.4 · ISO 27001 A.8.2",
        "Every admin account is a high-value target; the more there are, the larger the attack surface.",
        "A compromised admin account can disable security tools, delete backups and spread ransomware.",
        "Remove admin rights from daily-use accounts, keep a short named list of admins and require MFA on each.",
        "Medium", "Low"),
    "employee_access_control": ("IAM-04", "Role-based access control",
        "Is access to systems and data limited by job role (least privilege)?",
        "Answer Yes if staff only see the systems and files they need and access is removed when they leave.",
        "CIS 6.8 · ISO 27001 A.5.15",
        "Limiting access reduces the damage from a mistake or a stolen account.",
        "One compromised or careless account can expose the whole organisation's data.",
        "Define roles for common job types, remove shared accounts and review access every quarter.",
        "Medium", "Low"),
    "firewall_enabled": ("NET-01", "Network firewall",
        "Is a managed firewall protecting the network perimeter and endpoints?",
        "Includes a business router/firewall with maintained rules and host firewalls enabled on devices.",
        "CIS 4.4-4.5 · ISO 27001 A.8.20",
        "A firewall blocks unsolicited inbound connections and limits what can leave your network.",
        "Without it, internal systems are directly reachable from the internet and easier to scan and exploit.",
        "Enable the firewall on your router and every device, and close unused inbound ports.",
        "Low", "Low"),
    "network_segmentation": ("NET-02", "Network segmentation",
        "Are guest, IoT and business-critical systems on separate network segments?",
        "Answer Yes if guest Wi-Fi, cameras/printers and finance or server systems cannot reach each other freely.",
        "CIS 12.2 · ISO 27001 A.8.22",
        "Segmentation contains an intrusion to one area instead of letting it spread.",
        "A compromised camera, printer or guest device can become a stepping stone to critical systems.",
        "Create separate VLANs or SSIDs for guests, IoT devices and business systems.",
        "Medium", "Low"),
    "vpn_enabled": ("NET-03", "VPN for remote access",
        "Is a VPN or zero-trust gateway required for remote access to internal systems?",
        "Applies if staff work remotely or reach internal resources from outside the office.",
        "CIS 12.7 · ISO 27001 A.6.7",
        "A VPN encrypts remote connections and keeps internal services off the public internet.",
        "Exposed remote desktop or admin services are a leading ransomware entry point.",
        "Put remote access behind a VPN with MFA and disable direct remote-desktop exposure.",
        "Medium", "Low"),
    "remote_access": ("NET-04", "Remote access exposure",
        "Can staff or vendors log in to internal systems remotely?",
        "Answer Yes if any remote login to internal systems is possible. This is an exposure, not a control.",
        "ISO 27001 A.6.7 · CIS 12.7",
        "Every remote entry point is a potential door for attackers.",
        "Poorly secured remote access is a common route for account takeover and ransomware.",
        "Limit remote access to named users, require MFA and a VPN, and log all remote sessions.",
        "Medium", "Low"),
    "antivirus_enabled": ("END-01", "Anti-malware protection",
        "Is anti-malware software installed, updated and monitored on all business devices?",
        "Includes Windows Defender if it is centrally managed and kept up to date.",
        "CIS 10.1 · ISO 27001 A.8.7",
        "Anti-malware blocks known viruses, ransomware and malicious downloads.",
        "Unprotected devices let commodity malware run unnoticed.",
        "Enable managed endpoint protection on every laptop, desktop and server.",
        "Low", "Low"),
    "edr_enabled": ("END-02", "Endpoint detection & response (EDR)",
        "Is an EDR solution deployed on critical endpoints and servers?",
        "EDR monitors behaviour and can isolate a device automatically; it goes beyond classic antivirus.",
        "CIS 10.7 · ISO 27001 A.8.7",
        "EDR catches attacks that signature-based antivirus misses and speeds up response.",
        "Hands-on-keyboard attackers can operate for weeks without being detected.",
        "Deploy EDR (many vendors offer SME tiers) on servers and finance/admin laptops first.",
        "Medium", "Medium"),
    "device_encryption": ("END-03", "Device encryption",
        "Is full-disk encryption enabled on laptops and mobile devices?",
        "BitLocker (Windows), FileVault (macOS) or equivalent, with recovery keys stored safely.",
        "CIS 3.6 · ISO 27001 A.8.24",
        "Encryption keeps data unreadable if a device is lost or stolen.",
        "A lost laptop becomes a data breach with possible regulatory reporting duties.",
        "Turn on BitLocker or FileVault and escrow recovery keys centrally.",
        "Low", "Free"),
    "patch_management": ("VUL-01", "Patch management",
        "How current are operating systems and applications with security updates?",
        "Good: automatic updates and critical patches within 30 days. Average: patched irregularly. Poor: outdated or end-of-life systems in use.",
        "CIS 7.3-7.4 · ISO 27001 A.8.8",
        "Most attacks exploit known vulnerabilities that already have a patch available.",
        "Unpatched systems are exploited by automated tools within days of a vulnerability becoming public.",
        "Enable automatic updates, retire end-of-life systems and patch critical issues within 30 days.",
        "Medium", "Low"),
    "vulnerability_scanning": ("VUL-02", "Vulnerability scanning",
        "Are systems scanned for vulnerabilities on a regular schedule?",
        "At least quarterly for internal systems and any internet-facing services.",
        "CIS 7.5-7.6 · ISO 27001 A.8.8",
        "Scanning finds weaknesses before attackers do.",
        "Unknown vulnerabilities stay open for long periods.",
        "Schedule a monthly or quarterly scan with a low-cost or open-source scanner and track the fixes.",
        "Medium", "Low"),
    "critical_vulnerabilities": ("VUL-03", "Open critical vulnerabilities",
        "How many critical-severity vulnerabilities are currently known and unresolved?",
        "Use the latest scan or advisory results. Enter 0 if none.",
        "CIS 7.7 · ISO 27001 A.8.8",
        "Critical vulnerabilities are the most likely to be actively exploited.",
        "Each open critical issue is a ready-made entry point for attackers.",
        "Fix or isolate critical findings first, and set a 14-30 day deadline for them.",
        "Medium", "Low"),
    "asset_inventory": ("VUL-04", "Asset inventory",
        "Is an up-to-date inventory of devices, software and data stores maintained?",
        "A simple spreadsheet is acceptable if it is reviewed at least twice a year.",
        "CIS 1.1, 2.1 · ISO 27001 A.5.9",
        "You cannot protect or patch what you do not know you have.",
        "Forgotten devices and software become unmonitored weak points.",
        "Create an inventory of devices, servers, cloud services and key software, and review it twice a year.",
        "Low", "Free"),
    "backup_enabled": ("BCK-01", "Data backups",
        "Are business-critical data and systems backed up automatically?",
        "Answer Yes only for automated backups, not occasional manual copies.",
        "CIS 11.2 · ISO 27001 A.8.13",
        "Backups are the main way to recover from ransomware, accidental deletion or hardware failure.",
        "Without backups, an attack or failure can mean permanent data loss or paying a ransom.",
        "Set up automated backups to an offline or immutable cloud location, following the 3-2-1 rule.",
        "Low", "Low"),
    "backup_frequency": ("BCK-02", "Backup frequency",
        "How frequently do backups run?",
        "Choose the real interval for business-critical data. 'Unknown' means backups are not scheduled.",
        "CIS 11.2 · ISO 27001 A.8.13",
        "Backup frequency sets how much recent work you could lose.",
        "Monthly backups can mean losing up to a month of invoices, orders and records.",
        "Move critical data to daily backups and less critical data to weekly.",
        "Low", "Low"),
    "backup_tested": ("BCK-03", "Backup restore testing",
        "Are backup restores tested at least twice a year?",
        "A restore test means recovering real data from backup and confirming it is usable.",
        "CIS 11.5 · ISO 27001 A.8.13",
        "A backup that has never been restored may not work when it is needed.",
        "Failed or corrupt backups are often discovered only during an emergency.",
        "Schedule a restore test twice a year and record the result.",
        "Low", "Free"),
    "security_policy": ("GOV-01", "Information security policy",
        "Is there a written, approved information security policy that staff have read?",
        "It should cover acceptable use, passwords, data handling and incident reporting.",
        "ISO 27001 A.5.1 · NIST CSF GV.PO",
        "A policy sets clear rules and accountability for security.",
        "Without written rules, security depends on individual habit and is hard to enforce or audit.",
        "Adopt a short policy from a free CIS or SANS template and have staff acknowledge it.",
        "Low", "Free"),
    "incident_response_plan": ("GOV-02", "Incident response plan",
        "Is there a documented incident response plan with named contacts?",
        "It should say who to call, how to isolate systems, and who informs customers and authorities.",
        "CIS 17.4 · ISO 27001 A.5.24",
        "A plan turns panic into a rehearsed set of steps.",
        "Slow, unstructured responses increase downtime, cost and regulatory exposure.",
        "Write a one-to-two-page plan with roles, contacts and first-hour actions, and test it once a year.",
        "Low", "Free"),
    "business_continuity_plan": ("GOV-03", "Business continuity plan",
        "Is there a business continuity and disaster recovery plan covering critical systems?",
        "It should define how long each critical system can be down and how it is restored.",
        "ISO 27001 A.5.29-A.5.30 · NIST CSF RC.RP",
        "Continuity planning limits downtime after a major incident.",
        "Extended outages can cause lost revenue and permanent loss of customers.",
        "List critical systems, set recovery targets and document manual workarounds.",
        "Medium", "Low"),
    "security_training": ("AWR-01", "Security awareness training",
        "Do employees receive security awareness training at least annually?",
        "Include onboarding training for new staff.",
        "CIS 14.1 · ISO 27001 A.6.3",
        "Most breaches begin with a human mistake such as clicking a phishing link.",
        "Untrained staff are the easiest route into the organisation.",
        "Run short quarterly awareness sessions and onboarding training; free resources are available.",
        "Low", "Free"),
    "phishing_training": ("AWR-02", "Phishing simulations",
        "Are phishing simulations or drills run for employees?",
        "At least twice a year, with follow-up coaching for anyone who clicks.",
        "CIS 14.2 · ISO 27001 A.6.3",
        "Simulations measure and improve how staff handle real phishing emails.",
        "Phishing remains the leading initial attack vector for small businesses.",
        "Run quarterly phishing drills and coach staff who click.",
        "Low", "Low"),
    "data_encryption": ("DAT-01", "Data encryption",
        "Is sensitive data encrypted at rest and in transit?",
        "Includes databases, file shares, cloud storage and email transport encryption (TLS).",
        "CIS 3.9-3.11 · ISO 27001 A.8.24",
        "Encryption protects data even if storage or network traffic is intercepted.",
        "Unencrypted data turns any theft into a reportable data breach.",
        "Enable encryption on databases, cloud storage and backups, and enforce TLS for web and email.",
        "Medium", "Low"),
    "data_classification": ("DAT-02", "Data classification",
        "Is data classified by sensitivity (for example public, internal, confidential)?",
        "Answer Yes if staff know which data is confidential and how it must be handled.",
        "CIS 3.7 · ISO 27001 A.5.12",
        "Classification tells you where to spend protection effort.",
        "Sensitive personal data may be handled like ordinary files, raising breach and DPDP Act exposure.",
        "Define three classification levels and label the most confidential data stores first.",
        "Medium", "Free"),
    "cloud_security": ("DAT-03", "Cloud security",
        "How well are cloud services (storage, email, SaaS) configured and secured?",
        "Strong: MFA, least privilege, logging and reviewed sharing settings. Moderate: some controls. Weak: default or open settings.",
        "ISO 27001 A.5.23 · CIS 3, 6",
        "Misconfigured cloud services are a frequent cause of data exposure.",
        "Publicly shared files or weak cloud accounts can leak data without any 'hack'.",
        "Review sharing settings, enable MFA and logging on all cloud accounts and remove unused access.",
        "Medium", "Low"),
    "logging_enabled": ("MON-01", "Security logging",
        "Are system, authentication and network logs collected and retained?",
        "Keep at least 90 days of logs for critical systems.",
        "CIS 8.2 · ISO 27001 A.8.15",
        "Logs are the evidence needed to detect and investigate incidents.",
        "Without logs, you may never know what was accessed or how attackers got in.",
        "Enable logging on servers, firewalls and cloud services and retain at least 90 days.",
        "Low", "Low"),
    "siem_enabled": ("MON-02", "Centralised log monitoring (SIEM)",
        "Are logs centralised and analysed in a SIEM or similar tool?",
        "Managed and open-source options also count.",
        "CIS 8.9 · ISO 27001 A.8.15-A.8.16",
        "Central analysis spots patterns that individual logs hide.",
        "Attacks stay unnoticed for longer, increasing the damage.",
        "Start with a low-cost cloud log service or a managed detection service.",
        "High", "Medium"),
    "security_monitoring": ("MON-03", "Continuous security monitoring",
        "Is security monitored and alerted on continuously (24/7 or through a managed provider)?",
        "Alerts must reach someone who can act on them.",
        "ISO 27001 A.8.16 · CIS 13.1",
        "Fast detection limits how far an attack spreads.",
        "Out-of-hours attacks, which are common, go unnoticed until morning.",
        "Use a managed detection and response service or set alerts for logins and admin changes.",
        "High", "Medium"),
    "vendor_risk_assessment": ("TPR-01", "Vendor risk assessment",
        "Is the security of vendors and service providers assessed before and during engagement?",
        "A simple questionnaire or certificate review is acceptable.",
        "CIS 15.1-15.4 · ISO 27001 A.5.19-A.5.21",
        "A supplier breach can become your breach.",
        "Supply-chain weaknesses expose your data without any failure on your side.",
        "Keep a vendor list and ask critical vendors for security certifications or a short questionnaire.",
        "Medium", "Free"),
    "third_party_access": ("TPR-02", "Third-party access",
        "Do external parties (vendors, contractors) have access to internal systems or data?",
        "Answer Yes if any outside party can log in or reach company data. This is an exposure.",
        "ISO 27001 A.5.19 · CIS 15",
        "External access extends your attack surface beyond your own control.",
        "Compromised vendor credentials are a common route into customer networks.",
        "Give third parties time-limited, least-privilege access with MFA, and log their activity.",
        "Medium", "Low"),
    "previous_incidents": ("TPR-03", "Incident history",
        "Has the organisation experienced a cyber incident before?",
        "Include ransomware, account takeover, data leaks and significant malware.",
        "-",
        "Past incidents suggest attackers already know a way in, or that gaps still exist.",
        "Organisations that were attacked once are more likely to be targeted again.",
        "Complete a post-incident review and confirm the root cause is fixed.",
        "-", "-"),
    "incident_count_last_year": ("TPR-04", "Incidents in the last 12 months",
        "How many cyber incidents occurred in the last 12 months?",
        "Count incidents that disrupted operations or exposed data.",
        "-",
        "Recent incident frequency indicates how actively the organisation is being targeted.",
        "Repeated incidents point to unresolved root causes.",
        "Investigate each incident and track fixes to completion.",
        "-", "-"),
    "company_size": ("PRF-01", "Company size", "What is the size band of the organisation?",
                     "Used to calibrate expected controls and risk.", "-", "", "", "", "-", "-"),
    "industry": ("PRF-02", "Industry", "Which industry does the organisation operate in?",
                 "Sector affects the threats an organisation faces.", "-", "", "", "", "-", "-"),
    "annual_revenue": ("PRF-03", "Annual revenue", "What is the approximate annual revenue?",
                       "Use the same units as the model's training data (millions).", "-", "", "", "", "-", "-"),
    "employee_count": ("PRF-04", "Employees", "How many people work in the organisation?",
                       "Include full-time, part-time and long-term contractors.", "-", "", "", "", "-", "-"),
}
KB = {c: dict(zip(("id", "title", "q", "guide", "refs", "why", "impact", "fix", "effort", "cost"), v)) for c, v in KB.items()}

DOMAINS = [
    ("PRF", "Business Profile", "Organisation context used to calibrate the risk model.",
     ["company_size", "industry", "annual_revenue", "employee_count"]),
    ("IAM", "Identity & Access", "Who can log in, how strongly they are verified and what they can reach.",
     ["mfa_enabled", "password_policy", "privileged_accounts", "employee_access_control"]),
    ("NET", "Network Security", "Perimeter defences, segmentation and remote access exposure.",
     ["firewall_enabled", "network_segmentation", "vpn_enabled", "remote_access"]),
    ("END", "Endpoint Protection", "Protection of laptops, desktops, servers and mobile devices.",
     ["antivirus_enabled", "edr_enabled", "device_encryption"]),
    ("VUL", "Vulnerability & Patch Management", "How quickly weaknesses are found and fixed.",
     ["patch_management", "vulnerability_scanning", "critical_vulnerabilities", "asset_inventory"]),
    ("BCK", "Backup & Recovery", "Ability to restore data after ransomware, deletion or failure.",
     ["backup_enabled", "backup_frequency", "backup_tested"]),
    ("GOV", "Governance & Resilience", "Policies and plans that define how security and recovery are managed.",
     ["security_policy", "incident_response_plan", "business_continuity_plan"]),
    ("AWR", "Security Awareness", "How well people are prepared to recognise and report attacks.",
     ["security_training", "phishing_training"]),
    ("DAT", "Data Protection", "Protection of sensitive data in storage, transit and the cloud.",
     ["data_encryption", "data_classification", "cloud_security"]),
    ("MON", "Monitoring & Logging", "Detection capability: logs, alerts and continuous monitoring.",
     ["logging_enabled", "siem_enabled", "security_monitoring"]),
    ("TPR", "Third Parties & Incident History", "Supplier exposure and the organisation's incident track record.",
     ["vendor_risk_assessment", "third_party_access", "previous_incidents", "incident_count_last_year"]),
]
CONTROL_DOMAINS = [d for d in DOMAINS if d[0] != "PRF"]
PROFILE_COLS = {"company_size", "industry", "annual_revenue", "employee_count"}
EXPOSURE = {"remote_access", "third_party_access", "previous_incidents"}
NOT_FIXABLE = set(P.NOT_FIXABLE) | PROFILE_COLS
ORDERS = {"password_policy": ["Strong", "Moderate", "Weak"], "patch_management": ["Good", "Average", "Poor"],
          "cloud_security": ["Strong", "Moderate", "Weak"], "backup_frequency": ["Daily", "Weekly", "Monthly", "Unknown"],
          "company_size": ["Micro", "Small", "Medium"]}
ORDINAL = {"password_policy": {"strong": "good", "moderate": "mid", "weak": "bad"},
           "patch_management": {"good": "good", "average": "mid", "poor": "bad"},
           "cloud_security": {"strong": "good", "moderate": "mid", "weak": "bad"},
           "backup_frequency": {"daily": "good", "weekly": "good", "monthly": "mid", "unknown": "bad", "never": "bad"}}
PROTECTIVE = [c for c in KB if c not in PROFILE_COLS | EXPOSURE | {"privileged_accounts", "critical_vulnerabilities", "incident_count_last_year",
                                                                    "password_policy", "patch_management", "cloud_security", "backup_frequency"}]
TIER_COLOR = {"Low": "#15803D", "Medium": "#CA8A04", "High": "#EA580C", "Critical": "#DC2626"}
TIER_TEXT = {
    "Low": "The organisation shows a mature security posture with few material gaps. The priority is to sustain current controls and keep them reviewed.",
    "Medium": "The organisation has a reasonable baseline but meaningful gaps remain. Closing the highest-impact gaps would move it into the low-risk tier.",
    "High": "Several important controls are missing or weak, which materially raises the likelihood of a damaging incident. Prompt remediation is recommended.",
    "Critical": "Fundamental controls are missing and the organisation is highly exposed to common attacks such as phishing, ransomware and account takeover. Immediate remediation of the top gaps is strongly recommended.",
}
PHASES = [("Quick wins", "0-30 days", "Low"), ("Short term", "30-60 days", "Medium"), ("Strategic", "60-90 days", "High")]


def title(col):
    return KB.get(col, {}).get("title") or col.replace("_", " ").title()


def is_yes_no(col):
    return col in P.CAT and {v.lower() for v in P.CAT[col]["values"]} == {"yes", "no"}


def options(col):
    vals = list(P.CAT[col]["values"])
    if is_yes_no(col):
        return sorted(vals, key=lambda v: v.lower() != "yes")
    order = [o for o in ORDERS.get(col, []) if o in vals]
    return order + [v for v in vals if v not in order]


def classify(col, val):
    """Returns (css_class, label): good / mid / bad / info."""
    v = str(val)
    lv = v.lower()
    if col in PROFILE_COLS:
        return "info", v
    if col in EXPOSURE:
        return ("bad", "Yes - exposure") if lv == "yes" else ("good", "No")
    if col in ORDINAL:
        return ORDINAL[col].get(lv, "mid"), v
    if is_yes_no(col):
        return ("good", "Implemented") if lv == "yes" else ("bad", "Not implemented")
    try:
        n = float(val)
        limits = {"critical_vulnerabilities": (0, 2), "privileged_accounts": (3, 6), "incident_count_last_year": (0, 1)}[col]
        return ("good" if n <= limits[0] else "mid" if n <= limits[1] else "bad"), f"{n:g}"
    except Exception:
        return "mid", v


# --------------------------------------------------------------------------------------------- analysis helpers
def register_rows(record, impacts):
    rows = []
    for code, dname, _, cols in CONTROL_DOMAINS:
        for c in cols:
            if c not in record:
                continue
            cls, lab = classify(c, record[c])
            rows.append(dict(id=KB[c]["id"], domain=dname, col=c, control=KB[c]["title"], answer=str(_num(record[c])), cls=cls,
                             status=lab, impact=round(impacts.get(c, 0.0), 2), refs=KB[c]["refs"]))
    return rows


def domain_summary(record, impacts):
    out = []
    for code, name, desc, cols in CONTROL_DOMAINS:
        cols = [c for c in cols if c in record]
        net = sum(impacts.get(c, 0.0) for c in cols)
        cl = [classify(c, record[c])[0] for c in cols]
        out.append(dict(code=code, name=name, desc=desc, net=round(net, 2), good=cl.count("good"), mid=cl.count("mid"),
                        bad=cl.count("bad"), total=len(cols)))
    return out


def waterfall(impacts, top_n=7):
    base = P.base_value()
    pos = sorted([(c, v) for c, v in impacts.items() if v > 0.3], key=lambda kv: -kv[1])[:top_n]
    neg = sorted([(c, v) for c, v in impacts.items() if v < -0.3], key=lambda kv: kv[1])[:3]
    shown = {c for c, _ in pos + neg}
    other = sum(v for c, v in impacts.items() if c not in shown)
    steps = [(f"{title(c)}", v) for c, v in pos] + [(f"{title(c)}", v) for c, v in neg]
    if abs(other) >= 0.05:
        steps.append(("All other factors (net)", other))
    rows, cur = [], base
    for lab, v in steps:
        rows.append(dict(label=lab, delta=v, start=cur, end=cur + v))
        cur += v
    return base, rows, cur


def waterfall_geometry(ins):
    """Shared bar geometry (percent of a common axis) for the baseline and every waterfall row."""
    wf = ins["waterfall"]
    span = max(100.0, wf["base"] + sum(max(0, r["delta"]) for r in wf["rows"]))
    bars = [dict(label="Baseline (average organisation)", delta=None, left=0.0, width=wf["base"] / span * 100)]
    for r in wf["rows"]:
        lo, hi = min(r["start"], r["end"]), max(r["start"], r["end"])
        bars.append(dict(label=r["label"], delta=r["delta"], left=lo / span * 100, width=max(.8, (hi - lo) / span * 100)))
    return wf["base"], bars


def _num(v):
    try:
        f = float(v)
        return int(f) if f.is_integer() and not isinstance(v, str) else v
    except (TypeError, ValueError):
        return v


def plan_with_phases(record, top_k=14):
    plan = P.fix_plan(record, top_k=top_k)
    items = []
    for d in plan:
        kb = KB.get(d["column"], {})
        if d["column"] in NOT_FIXABLE or not kb or kb["effort"] == "-":
            continue
        items.append(dict(col=d["column"], title=kb["title"], frm=_num(d["from"]), to=_num(d["to"]), drop=d["drop"], effort=kb["effort"],
                          cost=kb["cost"], refs=kb["refs"], fix=kb["fix"], id=kb["id"]))
    groups = []
    for name, window, eff in PHASES:
        grp = sorted([i for i in items if i["effort"] == eff], key=lambda i: -i["drop"])
        groups.append((name, window, eff, grp))

    states, rec = [], dict(record)
    for _, _, _, grp in groups:
        for i in grp:
            rec[i["col"]] = i["to"]
        states.append(dict(rec))
    scores = [P.risk_score(record)] + P.risk_scores(states)
    phases = [dict(name=name, window=window, effort=eff, items=grp, before=scores[k], after=scores[k + 1])
              for k, (name, window, eff, grp) in enumerate(groups)]
    return items, phases


# --------------------------------------------------------------------------------------------- insights (AI or offline)
def build_insights(record, score, tier, impacts, org, use_llm):
    org_name = org.get("name") or "The organisation"
    industry, size, emp = record.get("industry", ""), record.get("company_size", ""), record.get("employee_count", "")
    base, wf_rows, _ = waterfall(impacts)
    pos = sorted([(c, v) for c, v in impacts.items() if v > 0 and c not in PROFILE_COLS], key=lambda kv: -kv[1])
    neg = sorted([(c, v) for c, v in impacts.items() if v < 0 and c not in PROFILE_COLS], key=lambda kv: kv[1])
    items, phases = plan_with_phases(record)
    reg = register_rows(record, impacts)
    gaps = [r for r in reg if r["cls"] == "bad"]
    total_pos = sum(v for _, v in pos) or 1.0
    top3_share = 100 * sum(v for _, v in pos[:3]) / total_pos
    final_after = phases[-1]["after"] if phases else score

    drop_map = {i["col"]: i["drop"] for i in items}
    drivers = []
    for rank, (c, v) in enumerate(pos[:8], 1):
        kb = KB[c]
        share = 100 * v / total_pos
        extra = f" Fixing it is modelled to lower the score by about {drop_map[c]:g} points." if c in drop_map else ""
        drivers.append(dict(col=c, id=kb["id"], title=kb["title"], value=str(_num(record[c])), points=round(v, 1), why=kb["why"],
                            impact=kb["impact"], fix=kb["fix"], effort=kb["effort"], cost=kb["cost"], refs=kb["refs"],
                            insight=f"{kb['title']} is currently recorded as '{_num(record[c])}'. It adds about {v:.1f} points to the risk score "
                                    f"({share:.0f}% of all risk-raising factors) and ranks #{rank} among the drivers of this assessment.{extra}"))
    strengths = [dict(col=c, title=KB[c]["title"], value=str(_num(record[c])), points=round(v, 1))
                 for c, v in neg if v <= -0.3 and classify(c, record[c])[0] == "good"][:4]
    domains = domain_summary(record, impacts)
    worst = sorted(domains, key=lambda d: -d["net"])[:2]

    exec_summary = (f"{org_name}{f' ({industry}, {size} business, {emp:g} employees)' if industry and size and isinstance(emp, (int, float)) else ''} "
                    f"has an overall cyber risk score of {score:g} out of 100, which places it in the {tier} risk tier. "
                    f"The assessment identified {len(gaps)} control gap{'s' if len(gaps) != 1 else ''}; the three largest drivers account for roughly "
                    f"{top3_share:.0f}% of the risk that sits above the model baseline. "
                    f"The weakest domains are {worst[0]['name']} and {worst[1]['name']}. "
                    f"Completing the recommended 90-day roadmap is projected to reduce the score from {score:g} to about {final_after:g}.")
    meaning = (TIER_TEXT[tier] + f" For context, an average organisation in the training data scores about {base:.0f}, so this organisation sits "
               f"{'above' if score > base else 'below'} the average by {abs(score - base):.0f} points.")
    outlook = (f"Focus first on the quick wins: they are low-effort, mostly low-cost and account for a large share of the achievable reduction. "
               f"Re-run the assessment after each phase to confirm progress.")
    action_notes = {i["col"]: i["fix"] for i in items}
    source = "Template-generated (offline mode)"

    if use_llm and P.llm_available():
        try:
            facts = {
                "organisation": org_name, "industry": industry, "size_band": size, "employees": emp, "risk_score": score, "risk_tier": tier,
                "average_organisation_score": round(base, 1), "controls_gaps": len(gaps),
                "top_risk_drivers": [dict(control_key=d["col"], title=d["title"], current_answer=d["value"], points_added=d["points"],
                                          why_it_matters=d["why"], business_impact=d["impact"]) for d in drivers[:6]],
                "strengths": [dict(title=s["title"], points_removed=abs(s["points"])) for s in strengths],
                "weakest_domains": [dict(name=d["name"], net_points=d["net"]) for d in worst],
                "roadmap": [dict(phase=p["name"], window=p["window"], projected_score_after=round(p["after"], 1),
                                 actions=[dict(control_key=i["col"], title=i["title"], change=f"{i['frm']} -> {i['to']}") for i in p["items"]])
                            for p in phases],
            }
            system = ("You are a senior cybersecurity risk analyst writing for the management of a small business. Use clear, professional English. "
                      "Use ONLY the facts provided. Never invent controls, numbers, incidents or products. Return ONLY valid JSON, no markdown.")
            user = ("Facts (JSON):\n" + json.dumps(facts) + "\n\nReturn JSON with exactly these keys:\n"
                    '{"executive_summary": "3-4 sentences for the CEO: score, tier, main reasons, what to do first",\n'
                    ' "score_meaning": "3-4 sentences explaining what this tier means for a business like this and how it compares with the average",\n'
                    ' "driver_insights": {"<control_key>": "2-3 sentences tailored to this organisation: what is wrong, why it matters, what could happen"},\n'
                    ' "action_notes": {"<control_key>": "1-2 sentences of practical, specific implementation advice"},\n'
                    ' "outlook": "2 sentences on expected improvement and next steps"}\n'
                    "Include driver_insights and action_notes only for the control_key values present in the facts.")
            raw = P.call_llm(system, user, max_tokens=2200)
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            clean = lambda s: " ".join(str(s).split())[:900]
            if data.get("executive_summary"):
                exec_summary = clean(data["executive_summary"])
            if data.get("score_meaning"):
                meaning = clean(data["score_meaning"])
            if data.get("outlook"):
                outlook = clean(data["outlook"])
            for d in drivers:
                t = (data.get("driver_insights") or {}).get(d["col"])
                if t:
                    d["insight"] = clean(t)
            for k, t in (data.get("action_notes") or {}).items():
                if k in action_notes and t:
                    action_notes[k] = clean(t)
            source = f"AI-generated ({P.llm_provider()})"
        except Exception as e:                       # keep the offline text, remember why
            P.LAST_ERROR = str(e)[:250]
            source = "Template-generated (AI unavailable: " + str(e)[:80] + ")"

    for ph in phases:
        for i in ph["items"]:
            i["note"] = action_notes.get(i["col"], i["fix"])
    return dict(executive_summary=exec_summary, meaning=meaning, outlook=outlook, drivers=drivers, strengths=strengths, domains=domains,
                register=reg, items=items, phases=phases, waterfall=dict(base=base, rows=wf_rows), source=source, gaps=len(gaps),
                top3_share=top3_share, projected=final_after, generated=datetime.now().strftime("%d %B %Y, %H:%M"))


# --------------------------------------------------------------------------------------------- shared SVG
def gauge_svg(score, width=300):
    def pt(f, r=90):
        a = math.pi * (1 - f)
        return 120 + r * math.cos(a), 120 - r * math.sin(a)
    arcs = ""
    for a, b, c in [(0, .25, "#15803D"), (.25, .5, "#EAB308"), (.5, .75, "#EA580C"), (.75, 1, "#DC2626")]:
        x1, y1 = pt(a + .006)
        x2, y2 = pt(b - .006)
        arcs += f'<path d="M {x1:.1f} {y1:.1f} A 90 90 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{c}" stroke-width="14"/>'
    mx, my = pt(max(0, min(1, score / 100)))
    return (f'<svg viewBox="0 0 240 160" width="{width}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">{arcs}'
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="9" fill="#fff" stroke="#0F2A47" stroke-width="3.5"/>'
            f'<text x="120" y="112" text-anchor="middle" font-size="42" font-weight="700" fill="#0F2A47">{score:g}</text>'
            f'<text x="120" y="134" text-anchor="middle" font-size="10" fill="#667085" letter-spacing="1.5">RISK SCORE / 100</text>'
            f'<text x="30" y="150" text-anchor="middle" font-size="10" fill="#98A2B3">0</text>'
            f'<text x="210" y="150" text-anchor="middle" font-size="10" fill="#98A2B3">100</text></svg>')


# --------------------------------------------------------------------------------------------- exports
def register_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Control ID", "Domain", "Control", "Response", "Status", "Risk contribution (points)", "Framework references"])
    for r in rows:
        w.writerow([r["id"], r["domain"], r["control"], r["answer"], r["status"], r["impact"], r["refs"]])
    return buf.getvalue()


def esc(s):
    return _h.escape(str(s))


REPORT_CSS = """
*{box-sizing:border-box} body{margin:0;background:#EEF1F6;font-family:'Segoe UI',Arial,sans-serif;color:#1B2B3C;font-size:13.5px;line-height:1.55}
.page{max-width:900px;margin:24px auto;background:#fff;box-shadow:0 2px 14px rgba(15,42,71,.12)}
.cover{background:#0F2A47;color:#fff;padding:38px 48px 30px}
.cover .brand{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:700;letter-spacing:.3px}
.cover h1{font-size:30px;margin:34px 0 4px;font-weight:700} .cover .sub{color:#B8C7DB;font-size:15px}
.meta{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:28px;border-top:1px solid #35516F;padding-top:16px}
.meta div{font-size:11px;color:#9FB3CC;text-transform:uppercase;letter-spacing:.8px} .meta b{display:block;color:#fff;font-size:13.5px;text-transform:none;letter-spacing:0;margin-top:2px}
.body{padding:28px 48px 36px} h2{font-size:18px;color:#0F2A47;border-bottom:2px solid #1F6FEB;padding-bottom:6px;margin:30px 0 14px;page-break-after:avoid}
h3{font-size:14.5px;color:#0F2A47;margin:18px 0 6px} p{margin:6px 0 10px}
.score-row{display:grid;grid-template-columns:300px 1fr;gap:26px;align-items:center;margin:8px 0}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:12px} .kpi{border:1px solid #DDE3EC;border-radius:8px;padding:12px 14px;border-top:3px solid #1F6FEB}
.kpi .l{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:#667085;font-weight:600} .kpi .v{font-size:24px;font-weight:700;color:#0F2A47}
.badge{display:inline-block;padding:3px 12px;border-radius:99px;font-weight:700;font-size:12px;color:#fff}
table{width:100%;border-collapse:collapse;margin:8px 0 14px;font-size:12.5px} th{background:#0F2A47;color:#fff;text-align:left;padding:8px 10px;font-weight:600}
td{padding:8px 10px;border-bottom:1px solid #E5EAF1;vertical-align:top} tr:nth-child(even) td{background:#F7F9FC} tr{page-break-inside:avoid}
.st{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11px;font-weight:600;white-space:nowrap}
.good{background:#DCFCE7;color:#166534}.mid{background:#FEF3C7;color:#92400E}.bad{background:#FEE2E2;color:#991B1B}.info{background:#E0E7FF;color:#3730A3}
.bar{height:9px;background:#E8ECF2;border-radius:99px;overflow:hidden;min-width:120px}.bar i{display:block;height:100%;border-radius:99px}
.callout{background:#F4F8FF;border-left:4px solid #1F6FEB;padding:12px 16px;border-radius:4px;margin:12px 0}
.driver{border:1px solid #DDE3EC;border-radius:8px;padding:12px 16px;margin:10px 0;page-break-inside:avoid}
.driver .h{display:flex;justify-content:space-between;font-weight:700;color:#0F2A47} .driver .h span{color:#DC2626}
.driver small{color:#667085}.driver .row{margin-top:6px}.driver .row b{color:#0F2A47}
.phase{margin:14px 0 4px;font-weight:700;color:#0F2A47}.phase span{color:#667085;font-weight:400}
.wf{position:relative;height:16px;background:#F0F3F8;border-radius:3px} .wf i{position:absolute;top:0;height:100%;border-radius:2px}
.foot{padding:16px 48px;background:#F7F9FC;border-top:1px solid #DDE3EC;color:#667085;font-size:11.5px}
.toolbar{max-width:900px;margin:16px auto 0;text-align:right} .toolbar button{background:#1F6FEB;color:#fff;border:0;border-radius:6px;padding:9px 18px;font-weight:600;cursor:pointer}
@page{size:A4;margin:14mm 12mm;@bottom-center{content:"RakshaScore - Confidential - Page " counter(page);font-size:9px;color:#777}}
@media print{body{background:#fff}.page{box-shadow:none;margin:0;max-width:none}.toolbar{display:none}.cover{-webkit-print-color-adjust:exact;print-color-adjust:exact}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact} h2{page-break-after:avoid}}
"""


def report_html(meta, res, ins):
    tier, score, color = res["tier"], res["score"], TIER_COLOR.get(res["tier"], "#1F6FEB")
    wf = ins["waterfall"]
    in_place = sum(1 for r in ins["register"] if r["cls"] == "good")

    def chip(cls, label):
        return f'<span class="st {cls}">{esc(label)}</span>'

    drivers = "".join(
        f'<div class="driver"><div class="h"><div>{i}. {esc(d["title"])} <small>({d["id"]})</small></div><span>+{d["points"]:g} points</span></div>'
        f'<div class="row"><small>Current response: <b>{esc(d["value"])}</b> &nbsp;|&nbsp; Effort: {d["effort"]} &nbsp;|&nbsp; Cost: {d["cost"]} &nbsp;|&nbsp; {esc(d["refs"])}</small></div>'
        f'<div class="row">{esc(d["insight"])}</div><div class="row"><b>Recommended action:</b> {esc(d["fix"])}</div></div>'
        for i, d in enumerate(ins["drivers"][:6], 1))

    domain_rows = "".join(
        f'<tr><td>{esc(d["code"])}</td><td>{esc(d["name"])}</td><td>{d["good"]}/{d["total"]}</td>'
        f'<td><div class="bar"><i style="width:{min(100, max(3, abs(d["net"]) / (max(abs(x["net"]) for x in ins["domains"]) or 1) * 100)):.0f}%;background:{"#DC2626" if d["net"] > 0 else "#15803D"}"></i></div></td>'
        f'<td><b>{d["net"]:+.1f}</b></td></tr>' for d in sorted(ins["domains"], key=lambda d: -d["net"]))

    base, bars = waterfall_geometry(ins)
    wf_rows = ""
    for b in bars:
        color = "#98A2B3" if b["delta"] is None else "#DC2626" if b["delta"] > 0 else "#15803D"
        points = f"{base:.1f}" if b["delta"] is None else f"{b['delta']:+.1f}"
        wf_rows += (f'<tr><td>{esc(b["label"])}</td><td><div class="wf"><i style="left:{b["left"]:.1f}%;'
                    f'width:{b["width"]:.1f}%;background:{color}"></i></div></td><td>{points}</td></tr>')
    wf_rows += f'<tr><td><b>Final risk score</b></td><td></td><td><b>{score:g}</b></td></tr>'

    register = "".join(
        f'<tr><td>{r["id"]}</td><td>{esc(r["control"])}<br><small style="color:#667085">{esc(r["domain"])}</small></td><td>{esc(r["answer"])}</td>'
        f'<td>{chip(r["cls"], r["status"])}</td><td>{r["impact"]:+.1f}</td><td><small>{esc(r["refs"])}</small></td></tr>' for r in ins["register"])

    roadmap = ""
    for ph in ins["phases"]:
        if not ph["items"]:
            continue
        rows = "".join(f'<tr><td>{esc(i["title"])}<br><small style="color:#667085">{esc(i["note"])}</small></td><td>{esc(i["frm"])} &rarr; {esc(i["to"])}</td>'
                       f'<td>{i["effort"]} / {i["cost"]}</td><td>-{i["drop"]:g}</td></tr>' for i in ph["items"])
        roadmap += (f'<div class="phase">{ph["name"]} <span>({ph["window"]}) &middot; projected score {ph["before"]:g} &rarr; <b style="color:#15803D">{ph["after"]:g}</b></span></div>'
                    f'<table><tr><th>Action</th><th>Change</th><th>Effort / Cost</th><th>Est. reduction</th></tr>{rows}</table>')
    strengths = "".join(f"<li><b>{esc(s['title'])}</b> (currently '{esc(s['value'])}') reduces the score by {abs(s['points']):g} points.</li>" for s in ins["strengths"]) or "<li>No standout strengths were identified.</li>"
    logo = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3z" fill="#1F6FEB"/><path d="m8.8 12.2 2.4 2.4 4-4.4" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Cyber Risk Assessment Report - {esc(meta['org'])}</title><style>{REPORT_CSS}</style></head><body>
<div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
<div class="page"><div class="cover"><div class="brand">{logo} RakshaScore</div>
<h1>Cyber Risk Assessment Report</h1><div class="sub">{esc(meta['org'])}</div>
<div class="meta"><div>Reference<b>{esc(meta['ref'])}</b></div><div>Assessment date<b>{esc(res['when'])}</b></div><div>Prepared by<b>{esc(meta['assessor'])}</b></div><div>Classification<b>Confidential</b></div></div></div>
<div class="body">
<h2>1. Executive summary</h2>
<div class="score-row"><div style="text-align:center">{gauge_svg(score, 280)}<div><span class="badge" style="background:{color}">{esc(tier.upper())} RISK</span></div></div>
<div class="kpis"><div class="kpi"><div class="l">Controls implemented</div><div class="v">{in_place}<span style="font-size:14px;color:#667085"> / {len(ins['register'])}</span></div></div>
<div class="kpi"><div class="l">Control gaps</div><div class="v">{ins['gaps']}</div></div>
<div class="kpi"><div class="l">Projected score (90 days)</div><div class="v" style="color:#15803D">{ins['projected']:g}</div></div>
<div class="kpi"><div class="l">Average organisation</div><div class="v">{wf['base']:.0f}</div></div></div></div>
<p>{esc(ins['executive_summary'])}</p><div class="callout"><b>What this score means.</b> {esc(ins['meaning'])}</div>
<p style="color:#667085;font-size:11.5px">Narrative source: {esc(ins['source'])}. Scope: {esc(meta['scope'])}</p>
<h2>2. How the score is composed</h2>
<p>The model starts from the average organisation and adds or removes points for each answer, using SHAP values. Red bars raise risk; green bars reduce it.</p>
<div style="page-break-inside:avoid"><table><tr><th style="width:36%">Factor</th><th>Contribution</th><th style="width:70px">Points</th></tr>{wf_rows}</table></div>
<h2>3. Key risk drivers</h2>{drivers}
<h3>What is working well</h3><ul>{strengths}</ul>
<div style="page-break-inside:avoid"><h2>4. Domain analysis</h2>
<table><tr><th style="width:55px">Code</th><th>Domain</th><th>Controls OK</th><th>Net risk contribution</th><th style="width:60px">Points</th></tr>{domain_rows}</table></div>
<h2>5. Remediation roadmap</h2><p>{esc(ins['outlook'])}</p>{roadmap}
<h2>6. Control register</h2>
<table><tr><th style="width:62px">ID</th><th>Control</th><th>Response</th><th>Status</th><th style="width:56px">Points</th><th>Framework</th></tr>{register}</table>
<h2>7. Methodology, assumptions and limitations</h2>
<ul><li>Responses were mapped to {len(ins['register'])} controls. A machine-learning model (gradient-boosted trees) estimates a 0-100 risk score; SHAP explains each answer's contribution.</li>
<li>The model was trained on a synthetic dataset built from published statistics, because no public labelled dataset of small-business breaches exists. Scores are therefore indicative, not validated predictions.</li>
<li>Framework references (CIS Controls v8, ISO/IEC 27001:2022 Annex A, NIST CSF) are an indicative mapping to help prioritise work and do not constitute a compliance assessment.</li>
<li>Answers are self-reported and have not been independently verified. This report does not replace a professional security audit or penetration test.</li></ul>
</div><div class="foot">RakshaScore Cyber Risk Assessment &middot; Reference {esc(meta['ref'])} &middot; Generated {esc(ins['generated'])} &middot; Confidential - for the named organisation only.</div></div></body></html>"""
