"""Helpers for the AI SDR agent. The agent finds leads with a buying signal through the Evaboot MCP,
qualifies each one against ICP.md and writes a two-email sequence for the ones that fit; these
commands keep the facts, the checks, the sheet and the Instantly push the same on every run. Only
`push` touches the network.

    python3 sdr.py facts <export.json> > queue/facts.json              signals and real hooks per lead
    python3 sdr.py check <facts.json> <sdr.json>                       decisions, emails, follow-ups
    python3 sdr.py sheet <facts.json> <sdr.json> [--max 20] > queue/queue.csv
    python3 sdr.py push <queue.csv> --campaign <id> [--send]          approved rows to Instantly
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request

SUBJECT_MAX = 60          # characters
BODY_WORDS = (40, 110)    # the first email
FOLLOWUP_WORDS = (20, 70)  # the second email, sent in the same thread if there is no reply
SCORES = range(1, 6)      # fit: 5 = exactly the ICP, 3 = worth a try, 1-2 = do not contact
# Phrases that mark an email as a template. Add your own to this list.
CLICHES = ["hope this finds you", "i hope you're well", "just checking in", "quick question", "touch base",
           "circle back", "synergy", "game-changer", "revolutionize", "i came across your profile",
           "just following up", "bumping this", "floating this", "any thoughts on my last email"]
SEND_STATUSES = {"safe"}  # only verified emails are pushed; "riskier" can bounce
LINK_DOMAINS = {"linktr.ee", "bit.ly", "beacons.ai", "lnk.bio", "linkin.bio", "carrd.co", "about.me"}
LINK = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|io|ai|co|net|org|app|dev|ee)\b", re.I)
CAP_NOTE = "Over today's cap"


def domain_note(email, company_domain):
    """Empty when the email domain matches the company's; otherwise a reason to look before sending."""
    if not email:
        return ""
    domain = email.rsplit("@", 1)[-1].lower()
    company = (company_domain or "").lower()
    if domain in LINK_DOMAINS:
        return f"email on {domain}, a link site: do not send"
    if company and not (domain == company or domain.endswith("." + company) or company.endswith("." + domain)):
        return f"email domain {domain} differs from the company's {company}: check it"
    return ""


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def facts(path):
    """export.json = the Evaboot export (get_export or the API). One entry per lead, only real fields."""
    out = []
    for p in json.load(open(path)).get("prospects") or []:
        years, mons = num(p.get("Years in Position")), num(p.get("Months in Position"))
        months = None if years is None and mons is None else (years or 0) * 12 + (mons or 0)
        out.append({
            "id": p.get("Linkedin URL Unique ID") or p.get("Linkedin URL Public") or p.get("Full Name"),
            "first_name": p.get("First Name") or "",
            "name": p.get("Full Name") or "",
            "email": p.get("Email") or "",
            "email_status": p.get("Email Status") or "not found",
            "email_check": domain_note(p.get("Email") or "", p.get("Company Domain")),
            "title": (p.get("Current Job") or "").strip(),
            "company": p.get("Company Name") or "",
            "industry": p.get("Company Industry") or "",
            "employees": num(p.get("Company Employee Exact Count")),
            "employee_range": p.get("Company Employee Range") or "",
            "company_growth_1y_pct": num(p.get("Company Employee Growth 1 Year (%)")),
            "sales_team": num(p.get("Sales Team Size")),
            "months_in_role": months,
            "new_in_role": str(p.get("Has New Position")).lower() in ("true", "yes", "1")
                           or (months is not None and months < 6),
            "headline": " ".join((p.get("Profile Headline") or "").split()),
            "summary": " ".join((p.get("Profile Summary") or "").split())[:700],
            "company_description": " ".join((p.get("Company Description") or "").split())[:400],
            "linkedin": p.get("Linkedin URL Public") or "",
        })
    return out


def words(text):
    return len(text.split())


def check(facts_path, sdr_path):
    """Every lead gets a decision with a reason. A fit (3 or more) gets a hook, an email and a follow-up."""
    leads = {f["id"]: f for f in json.load(open(facts_path))}
    entries = json.load(open(sdr_path))
    problems, openings = [], {}
    for e in entries:
        lead = leads.get(e.get("id"))
        if not lead:
            problems.append(f"unknown lead {e.get('id')}")
            continue
        who = lead["name"]
        if e.get("score") not in SCORES or not e.get("reason"):
            problems.append(f"{who}: needs a score from 1 to 5 and a reason")
            continue
        if e["score"] < 3:
            continue
        if lead["email_status"] not in SEND_STATUSES or "do not send" in lead.get("email_check", ""):
            if not e.get("skip"):
                problems.append(f"{who}: no safe email, mark the lead skip with the reason")
            continue
        subject, body, follow = e.get("subject", ""), e.get("body", ""), e.get("followup", "")
        if not e.get("hook"):
            problems.append(f"{who}: no hook named")
        if not subject or len(subject) > SUBJECT_MAX:
            problems.append(f"{who}: subject empty or over {SUBJECT_MAX} characters")
        elif subject != subject.lower():
            problems.append(f"{who}: write the subject in lower case")
        if not BODY_WORDS[0] <= words(body) <= BODY_WORDS[1]:
            problems.append(f"{who}: email is {words(body)} words, keep it between {BODY_WORDS[0]} and {BODY_WORDS[1]}")
        if not FOLLOWUP_WORDS[0] <= words(follow) <= FOLLOWUP_WORDS[1]:
            problems.append(f"{who}: follow-up is {words(follow)} words, keep it between "
                            f"{FOLLOWUP_WORDS[0]} and {FOLLOWUP_WORDS[1]}")
        for label, text in (("email", body), ("follow-up", follow)):
            if LINK.search(text):
                problems.append(f"{who}: a link or a domain in the {label} hurts deliverability")
            plain = text.lower().replace("\u2019", "'")
            for c in CLICHES:
                if c in plain:
                    problems.append(f'{who}: template phrase "{c}" in the {label}')
        first = re.split(r"[\s-]", lead["first_name"].strip())[0].lower()  # "Cristian-Daniel" -> "cristian"
        if not first or not re.match(rf"hi {re.escape(first)}\b", body.lower()):
            problems.append(f"{who}: open the email with the first name")
        long_sentences = [x.strip() for x in re.split(r"[.?!\n]", body) if words(x) >= 8]
        if any(x.lower() in follow.lower() for x in long_sentences):
            problems.append(f"{who}: the follow-up repeats a sentence of the email, add something new")
        opening = " ".join(body.split(".")[0].split()[2:7]).lower()
        openings[opening] = openings.get(opening, 0) + 1
    written = sum(1 for e in entries if e.get("score", 0) >= 3 and e.get("body"))
    for o, c in openings.items():
        if written >= 6 and c > written / 3:
            problems.append(f'{c} of {written} emails open the same way ("{o}..."): vary it')
    missing = set(leads) - {e.get("id") for e in entries}
    problems += [f"no decision for {leads[i]['name']}" for i in missing]
    for p in problems:
        print("FAIL", p)
    fits = sum(1 for e in entries if e.get("score", 0) >= 3)
    print(f"{len(entries)} leads: {fits} fit, {len(entries) - fits} not a fit, {written} sequences written, "
          f"{len(problems)} problems")
    return 1 if problems else 0


def sheet(facts_path, sdr_path, cap):
    """Best fit first. Rows over today's cap stay in the sheet for the next run."""
    entries = {e["id"]: e for e in json.load(open(sdr_path))}
    rows = [(f, entries.get(f["id"], {})) for f in json.load(open(facts_path))]
    rows.sort(key=lambda r: (-(r[1].get("score") or 0), bool(r[1].get("skip"))))
    w = csv.writer(sys.stdout)
    w.writerow(["Name", "Title", "Company", "Fit (1-5)", "Why", "Email", "Email status", "Email check", "Hook",
                "Subject", "Email 1", "Follow-up", "Send (yes/no)"])
    written = 0
    for f, e in rows:
        why = e.get("reason", "")
        ready = (e.get("score") or 0) >= 3 and e.get("body") and not e.get("skip")
        if ready:
            written += 1
            if written > cap:
                why = f"{CAP_NOTE} of {cap}: next run. " + why
        w.writerow([f["name"], f["title"], f["company"], e.get("score", ""), why, f["email"], f["email_status"],
                    f.get("email_check", ""), e.get("hook", "") if ready else "",
                    e.get("subject", "") if ready else "", e.get("body", "") if ready else "",
                    e.get("followup", "") if ready else "", ""])


def instantly(method, path, body=None):
    key = os.environ.get("INSTANTLY_API_KEY")
    if not key:
        sys.exit("INSTANTLY_API_KEY is not set: put it in .env and load it (set -a; . ./.env; set +a)")
    headers = {"Authorization": "Bearer " + key, "User-Agent": "ai-sdr-agent/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("https://api.instantly.ai/api/v2" + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:300]}")


def campaign_ok(campaign):
    """An SDR stops the moment a person answers. Refuse a campaign that would keep emailing them."""
    c = instantly("GET", f"/campaigns/{campaign}")
    problems = []
    if c.get("stop_on_reply") is not True:
        problems.append("stop on reply is off")
    if c.get("stop_for_company") is not True:
        problems.append("stop for the company on reply is off")
    steps = (c.get("sequences") or [{}])[0].get("steps") or []
    texts = json.dumps(steps)
    for var in ("{{ai_subject}}", "{{personalization}}", "{{ai_followup}}"):
        if var not in texts:
            problems.append(f"no {var} in the sequence")
    for p in problems:
        print(f"campaign {c.get('name', campaign)}: {p} (see docs/instantly.md)")
    return not problems


def push(queue_path, campaign, send):
    """Rows marked yes, with a safe email, go to the campaign as leads: the first email in
    `personalization`, the subject in `ai_subject` and the follow-up in `ai_followup`."""
    if not campaign_ok(campaign):
        sys.exit("fix the campaign first: nothing was pushed")
    rows = [r for r in csv.DictReader(open(queue_path))
            if r["Send (yes/no)"].strip().lower() == "yes" and r["Email 1"]]
    for r in [r for r in rows if r["Why"].startswith(CAP_NOTE)]:
        print(f"skip {r['Name']}: over today's cap, it waits for the next run")
        rows.remove(r)
    ready = [r for r in rows if r["Email status"] in SEND_STATUSES and r["Email"]
             and "do not send" not in r.get("Email check", "")]
    for r in rows:
        if r not in ready:
            print(f"skip {r['Name']}: {r.get('Email check') or 'email status ' + (r['Email status'] or 'missing')}")
    added = 0
    already = set()
    if send:  # people loaded by an earlier run of this push
        already = {x["email"].lower() for x in instantly("POST", "/leads/list", {"campaign": campaign, "limit": 100})
                   .get("items", [])}
    for r in ready:
        first, _, last = r["Name"].partition(" ")
        lead = {"campaign": campaign, "email": r["Email"], "first_name": first, "last_name": last,
                "company_name": r["Company"], "personalization": r["Email 1"],
                "custom_variables": {"ai_subject": r["Subject"], "ai_followup": r["Follow-up"]},
                "skip_if_in_campaign": True}
        if not send:
            print(f"dry run: {r['Name']} <{r['Email']}>")
            continue
        if r["Email"].lower() in already:
            print(f"skip {r['Name']}: already in this campaign")
            continue
        # Instantly answers 200 with the existing lead when the person is already in a campaign.
        other = instantly("POST", "/leads", lead).get("campaign")
        if other and other != campaign:
            print(f"skip {r['Name']}: already in campaign {other}, never two sequences at once")
            continue
        added += 1
        print(f"added: {r['Name']} <{r['Email']}>")
    print(f"{added if send else len(ready)} of {len(rows)} approved rows "
          f"{'added to' if send else 'ready for'} campaign {campaign}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("facts"); a.add_argument("export")
    a = sub.add_parser("check"); a.add_argument("facts"); a.add_argument("sdr")
    a = sub.add_parser("sheet"); a.add_argument("facts"); a.add_argument("sdr")
    a.add_argument("--max", type=int, default=20, help="sequences a day; the rest wait for the next run")
    a = sub.add_parser("push"); a.add_argument("queue"); a.add_argument("--campaign", required=True)
    a.add_argument("--send", action="store_true", help="really add the leads; without it, a dry run")
    args = ap.parse_args()
    if args.cmd == "facts":
        print(json.dumps(facts(args.export), indent=2, ensure_ascii=False))
    elif args.cmd == "check":
        sys.exit(check(args.facts, args.sdr))
    elif args.cmd == "sheet":
        sheet(args.facts, args.sdr, args.max)
    else:
        push(args.queue, args.campaign, args.send)


if __name__ == "__main__":
    main()
