"""Builds n8n/ai-sdr-agent.json. Run: python3 n8n/build_workflow.py

Two entry points in one workflow:

1. Evaboot posts new leads: a recurring export of your signal search (weekly or daily) sends only the
   new people to this webhook. Claude scores each one against your ICP and writes a two-email sequence
   for the ones that fit, a Code node applies the same checks as sdr.py, and the rows land in your sheet,
   best fit first, with anything over your daily cap marked for the next run.
2. When you have marked rows "yes", you submit the approval form: the workflow checks that the
   Instantly campaign stops on reply, reads the sheet back and adds the approved, safe rows. A person
   who is already in another campaign is skipped. Nothing is sent: you launch the campaign.
"""
import json
import uuid
from pathlib import Path

ANTHROPIC_CRED = {"anthropicApi": {"id": "", "name": "Anthropic"}}
SHEETS_CRED = {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets account"}}
INSTANTLY_CRED = {"httpHeaderAuth": {"id": "", "name": "Instantly API key"}}
MODEL = "claude-sonnet-5-5"

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, kind="main", out=0):
    connections.setdefault(a, {}).setdefault(kind, [])
    while len(connections[a][kind]) <= out:
        connections[a][kind].append([])
    connections[a][kind][out].append({"node": b, "type": kind, "index": 0})


def code(name, js, pos, **extra):
    node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


def settings(name, pos):
    node(name, "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
        {"id": str(uuid.uuid4()), "name": k, "type": "string", "value": v} for k, v in [
            ("daily_cap", "20"),
            ("sheet_url", "PASTE_YOUR_GOOGLE_SHEET_URL_WITH_GID"),
            ("instantly_campaign_id", "PASTE_YOUR_CAMPAIGN_ID"),
            ("icp", "Size first: a company over 1,000 employees is a 2, whatever the role. Fit 5: VP Sales, Head of Sales, CRO, Head of SDRs or RevOps at a B2B software company of 50 to "
                    "1,000 employees with 10+ sellers or 20%+ growth in a year. 4: same role, 3 to 9 sellers, or B2B "
                    "not software. 3: under 50 employees, commercial operations, or a business unit under 1,000 inside a larger group. "
                    "2: over 1,000 employees, partnerships, B2C. 1: M&A, investors, fractional or consulting roles, "
                    "founders of under 10 people."),
            ("offer", "Evaboot exports a LinkedIn Sales Navigator search to a clean spreadsheet with verified "
                      "professional emails; a saved search can export the new leads every week. For sales leaders "
                      "who build prospect lists. Ask: a low-effort question such as 'Worth a look?'"),
        ]]}, "includeOtherFields": True, "options": {}}, pos)


FACTS_JS = r"""
// Same as sdr.py facts: real fields only, plus the email-domain check.
const LINK_DOMAINS = ['linktr.ee', 'bit.ly', 'beacons.ai', 'lnk.bio', 'linkin.bio', 'carrd.co', 'about.me'];
const num = v => { const n = parseFloat(String(v ?? '').replace(/,/g, '')); return isNaN(n) ? null : n; };
const words = s => String(s || '').split(/\s+/).join(' ').trim();
function domainNote(email, company) {
  if (!email) return '';
  const d = email.split('@').pop().toLowerCase(); const c = String(company || '').toLowerCase();
  if (LINK_DOMAINS.includes(d)) return `email on ${d}, a link site: do not send`;
  if (c && !(d === c || d.endsWith('.' + c) || c.endsWith('.' + d))) return `email domain ${d} differs from the company's ${c}: check it`;
  return '';
}
// Evaboot posts one request per export, with every lead in body.prospects.
const prospects = $('New leads from Evaboot').first().json.body.prospects || [];
if (!prospects.length) return [];
const leads = prospects.map(p => {
  const months = (num(p['Years in Position']) || 0) * 12 + (num(p['Months in Position']) || 0);
  return {
    id: p['Linkedin URL Unique ID'] || p['Linkedin URL Public'] || p['Full Name'],
    first_name: p['First Name'] || '', name: p['Full Name'] || '',
    email: p['Email'] || '', email_status: p['Email Status'] || 'not found',
    email_check: domainNote(p['Email'] || '', p['Company Domain']),
    title: String(p['Current Job'] || '').trim(), company: p['Company Name'] || '',
    industry: p['Company Industry'] || '', employees: num(p['Company Employee Exact Count']),
    company_growth_1y_pct: num(p['Company Employee Growth 1 Year (%)']), sales_team: num(p['Sales Team Size']),
    months_in_role: months,
    new_in_role: ['true', 'yes', '1'].includes(String(p['Has New Position']).toLowerCase()) || months < 6,
    headline: words(p['Profile Headline']), summary: words(p['Profile Summary']).slice(0, 700),
    company_description: words(p['Company Description']).slice(0, 400),
  };
});
return [{ json: { leads } }];
"""

ROWS_JS = r"""
// Same checks as sdr.py check, then best fit first and the daily cap.
const leads = $('Lead facts').first().json.leads;
const cap = Number($('Your settings').first().json.daily_cap) || 20;
const out = Object.fromEntries($json.output.leads.map(e => [e.id, e]));
const n = s => String(s || '').split(/\s+/).filter(Boolean).length;
const CLICHES = ['hope this finds you', 'quick question', 'just checking in', 'just following up', 'circle back', 'game-changer'];
const rows = leads.map(l => {
  const e = out[l.id] || { score: 0, reason: 'no decision returned' };
  const fit = (e.score || 0) >= 3 && !e.skip;
  const first = String(l.first_name).split(/[\s-]/)[0].toLowerCase();
  const text = ((e.body || '') + ' ' + (e.followup || '')).toLowerCase();
  const bad = fit && (!e.hook || !e.subject || e.subject.length > 60 || n(e.body) < 40 || n(e.body) > 110
    || n(e.followup) < 20 || n(e.followup) > 70 || /https?:\/\/|www\./.test(text)
    || !String(e.body).toLowerCase().startsWith('hi ' + first) || CLICHES.some(c => text.includes(c)));
  const ok = fit && !bad && l.email_status === 'safe' && !l.email_check.includes('do not send');
  return { score: e.score || 0, ok, json: {
    'Name': l.name, 'Title': l.title, 'Company': l.company, 'Fit (1-5)': e.score || '',
    'Why': bad ? 'The sequence failed the checks. ' + (e.reason || '') : (e.reason || ''),
    'Email': l.email, 'Email status': l.email_status, 'Email check': l.email_check,
    'Hook': ok ? e.hook : '', 'Subject': ok ? e.subject : '', 'Email 1': ok ? e.body : '',
    'Follow-up': ok ? e.followup : '', 'Send (yes/no)': '',
  } };
});
rows.sort((a, b) => b.score - a.score);
let written = 0;
for (const r of rows) if (r.ok && ++written > cap) r.json['Why'] = `Over today's cap of ${cap}: next run. ` + r.json['Why'];
return rows.map(r => ({ json: r.json }));
"""

GUARD_JS = r"""
// sdr.py campaign_ok: refuse a campaign that would keep emailing a person who answered.
const c = $json, steps = JSON.stringify(((c.sequences || [])[0] || {}).steps || []);
const problems = [];
if (c.stop_on_reply !== true) problems.push('stop on reply is off');
for (const v of ['{{ai_subject}}', '{{personalization}}', '{{ai_followup}}'])
  if (!steps.includes(v)) problems.push(`no ${v} in the sequence`);
if (problems.length) throw new Error(`Fix the Instantly campaign first (${problems.join(', ')}). Nothing was loaded.`);
return [{ json: { campaign: c.name } }];
"""

APPROVED_JS = r"""
// Rows you marked yes, with a safe email that is not on a link site.
return $input.all().filter(r => String(r.json['Send (yes/no)']).trim().toLowerCase() === 'yes'
  && r.json['Email 1'] && r.json['Email status'] === 'safe' && !String(r.json['Email check']).includes('do not send'));
"""

RESULT_JS = r"""
// Instantly answers with the existing lead when the person is already in another campaign.
const mine = $('Approval settings').first().json.instantly_campaign_id;
const rows = $('Approved rows').all();
const added = [], skipped = [];
$input.all().forEach((r, i) => (r.json.campaign === mine ? added : skipped).push(rows[i].json['Name']));
return [{ json: { added: added.length, skipped_already_in_a_campaign: skipped } }];
"""

WRITE_SYSTEM = """You are an SDR. For each lead in the JSON you are given, score the fit against the ICP below from 1 to 5 and give the reason in one line, from the facts only. For every lead with a score of 3 or more, write a two-email sequence for the offer below. Use only the facts in the JSON and the offer: never invent a customer, a number or a result.

Return {id, score, reason} for every lead, plus {hook, subject, body, followup} for a fit, or skip: true when the lead has no email, an email_status other than safe, or an email_check that says "do not send".
Email 1: subject of 60 characters at most, lower case, about them. Body of 40 to 110 words: "Hi <first name>," then one short paragraph on them, one on the offer, one line for a low-effort ask; paragraphs separated by a blank line. One real hook, named in "hook": a new role, company growth (always "in a year"), the size of the sales team, or one concrete line of their own headline or summary.
Follow-up (sent 3 days later in the same thread if there is no reply): 20 to 70 words, starts with "Hi <first name>,", gives one new angle, never repeats a sentence of email 1, never "just following up".
No link, no template phrases ("hope this finds you", "quick question"), and vary the first line across the emails.

ICP:
{{ $('Your settings').first().json.icp }}

Offer:
{{ $('Your settings').first().json.offer }}"""

# 1. New leads from the recurring export
node("New leads from Evaboot", "n8n-nodes-base.webhook", 2, {
    "httpMethod": "POST", "path": "evaboot-ai-sdr", "responseMode": "onReceived", "options": {},
}, [0, 0], webhookId=str(uuid.uuid4()))
settings("Your settings", [220, 0])
code("Lead facts", FACTS_JS, [440, 0])
node("Qualify and write", "@n8n/n8n-nodes-langchain.agent", 2.2, {
    "promptType": "define", "text": "={{ JSON.stringify($json.leads) }}", "hasOutputParser": True,
    "options": {"systemMessage": "=" + WRITE_SYSTEM, "maxIterations": 3},
}, [680, 0], retryOnFail=True, maxTries=3, waitBetweenTries=2000)
node("Claude", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.3, {
    "model": {"__rl": True, "mode": "list", "value": MODEL, "cachedResultName": MODEL},
    "options": {"maxTokensToSample": 16000},
}, [640, 220], ANTHROPIC_CRED)
node("Decisions", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.3, {
    "schemaType": "manual",
    "inputSchema": json.dumps({"type": "object", "required": ["leads"], "properties": {"leads": {
        "type": "array", "items": {"type": "object", "required": ["id", "score", "reason"], "properties": {
            "id": {"type": "string"}, "score": {"type": "integer"}, "reason": {"type": "string"},
            "hook": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"},
            "followup": {"type": "string"}, "skip": {"type": "boolean"}}}}}}, indent=2),
}, [800, 220])
code("Check, rank and cap", ROWS_JS, [1000, 0])
node("Add to the approval sheet", "n8n-nodes-base.googleSheets", 4.7, {
    "operation": "append",
    "documentId": {"__rl": True, "mode": "url", "value": "={{ $('Your settings').first().json.sheet_url }}"},
    "sheetName": {"__rl": True, "mode": "url", "value": "={{ $('Your settings').first().json.sheet_url }}"},
    "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
    "options": {},
}, [1220, 0], SHEETS_CRED)

# 2. The approval
node("Load approved rows", "n8n-nodes-base.formTrigger", 2.2, {
    "formTitle": "Load the approved sequences",
    "formDescription": "Write yes in Send for the rows to load, then submit. Only safe emails are loaded, and nobody who is already in a campaign. Nothing is sent: you launch the campaign in Instantly.",
    "formFields": {"values": [{"fieldLabel": "I have read the sequences marked yes", "fieldType": "checkbox",
                               "fieldOptions": {"values": [{"option": "Yes"}]}, "requiredField": True}]},
    "responseMode": "lastNode", "options": {},
}, [0, 400])
settings("Approval settings", [220, 400])
node("Read the campaign", "n8n-nodes-base.httpRequest", 4.2, {
    "url": "=https://api.instantly.ai/api/v2/campaigns/{{ $json.instantly_campaign_id }}",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "options": {},
}, [440, 400], INSTANTLY_CRED)
code("Stops on reply?", GUARD_JS, [660, 400])
node("Read the sheet", "n8n-nodes-base.googleSheets", 4.7, {
    "operation": "read",
    "documentId": {"__rl": True, "mode": "url", "value": "={{ $('Approval settings').first().json.sheet_url }}"},
    "sheetName": {"__rl": True, "mode": "url", "value": "={{ $('Approval settings').first().json.sheet_url }}"},
    "options": {},
}, [880, 400], SHEETS_CRED)
code("Approved rows", APPROVED_JS, [1100, 400])
node("Add to Instantly", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST", "url": "https://api.instantly.ai/api/v2/leads",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
    "sendBody": True, "specifyBody": "json",
    "jsonBody": "={{ JSON.stringify({ campaign: $('Approval settings').first().json.instantly_campaign_id, "
                "email: $json.Email, first_name: $json.Name.split(' ')[0], "
                "last_name: $json.Name.split(' ').slice(1).join(' '), company_name: $json.Company, "
                "personalization: $json['Email 1'], "
                "custom_variables: { ai_subject: $json.Subject, ai_followup: $json['Follow-up'] }, "
                "skip_if_in_campaign: true }) }}",
    "options": {},
}, [1320, 400], INSTANTLY_CRED)
code("Added or skipped", RESULT_JS, [1540, 400])
node("Loaded", "n8n-nodes-base.form", 2.3, {
    "operation": "completion", "completionTitle": "Sequences loaded",
    "completionMessage": "={{ $json.added }} added to your Instantly campaign. Already in a campaign, so skipped: "
                         "{{ $json.skipped_already_in_a_campaign.join(', ') || 'nobody' }}. Preview a few leads, "
                         "then launch the campaign when you are ready.",
    "options": {}}, [1760, 400])

for a, b in [("New leads from Evaboot", "Your settings"), ("Your settings", "Lead facts"),
             ("Lead facts", "Qualify and write"),
             ("Qualify and write", "Check, rank and cap"), ("Check, rank and cap", "Add to the approval sheet"),
             ("Load approved rows", "Approval settings"), ("Approval settings", "Read the campaign"),
             ("Read the campaign", "Stops on reply?"), ("Stops on reply?", "Read the sheet"),
             ("Read the sheet", "Approved rows"), ("Approved rows", "Add to Instantly"),
             ("Add to Instantly", "Added or skipped"), ("Added or skipped", "Loaded")]:
    link(a, b)
link("Claude", "Qualify and write", "ai_languageModel")
link("Decisions", "Qualify and write", "ai_outputParser")

workflow = {"name": "AI SDR agent (Evaboot + Claude + Instantly)", "nodes": nodes,
            "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("ai-sdr-agent.json")
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
