---
name: ai-sdr
description: Run an AI SDR on real data - watch a Sales Navigator search for a buying signal (new sales leaders), export the new people with verified emails through Evaboot, score each one against the ICP with a one-line reason, write a two-email sequence (first email and follow-up) for the ones that fit, check every email, queue them in a sheet for approval with a daily cap, and load the approved ones into an Instantly campaign that stops on reply. Use when the user asks for an AI SDR, an AI SDR agent, to automate outbound prospecting with AI, or to qualify and email new leads every week.
---

# AI SDR

This skill runs inside a clone of https://github.com/evaboot-labs/ai-sdr-agent: it uses the repo's `sdr.py`, `ICP.md` and `docs/`. If `sdr.py` is not in the working directory, clone the repo and work from there.

You do the Sales Navigator and Evaboot work through the Evaboot MCP server (`https://mcp.evaboot.com/mcp`). Every tool named below is an Evaboot MCP tool. You score the leads and write the emails yourself. `sdr.py` turns the export into facts, checks your work, builds the sheet and, with `--send`, pushes approved rows to Instantly.

## Rules

- **Nothing is sent from this skill.** The push only adds leads to an Instantly campaign; the user launches it.
- Confirm with the user before every call that spends credits or writes somewhere: `export_sn_search_or_list`, `create_recurring_export`, and `sdr.py push --send`. Show the count and the cost (1 Evaboot credit per exported lead), then wait for a yes.
- Score and write only from that lead's facts in `queue/facts.json` and from `ICP.md`. Never invent a customer, a number or a result.
- Never ask for or paste an API key. The user writes `EVABOOT_API_KEY` and `INSTANTLY_API_KEY` into `.env`.
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.

## Step 0: check the setup

1. If the Evaboot MCP tools are not in this session, walk the user through `docs/connect-your-agent.md`, then ask them to restart the agent from this folder: `EVABOOT_API_KEY` is read only when the agent starts.
2. Otherwise call `verify_token` and `get_daily_export_quota`. If `has_valid_salesnav` is false, ask the user to sign in to Evaboot in Chrome, open any Sales Navigator search with the Evaboot extension, and click Export with Evaboot, then call the quota again.
3. Run `mkdir -p data queue`, and `cp .env.example .env` if `.env` is missing (the user fills in the keys).
4. Read `ICP.md`. If it says `Status: EXAMPLE`, ask the user what they sell, to whom (roles, company size, industry), what proof they may use, their ask and their daily cap. Rewrite the file and set `Status: yours`.

## Step 1: the signal search

1. Call `build_sn_search_from_prompt` with **people only**: the ICP's titles and geography, plus the signal ("changed jobs in the last 90 days"). Never put an industry or a company size in this request: that starts a company-first crawl.
2. Poll `get_search_build`, then add the industry and size filters to the URL yourself (`INDUSTRY` and `COMPANY_HEADCOUNT`, as the account's other searches use them).
3. Call `search_sn_leads` on the URL with `count: 25`. It is free. Show the total and the first titles and companies. Tighten the search if the list is noisy.
4. On a yes, call `export_sn_search_or_list` with `max_results` (the daily cap, or a little more), and poll `get_export` with `limit: 0` until `EXECUTED`.
5. Save the leads to `data/export.json` with the Evaboot API (the key is in `.env`): `set -a; . ./.env; set +a; curl -s -H "Authorization: Bearer $EVABOOT_API_KEY" https://api.evaboot.com/v1/extractions/<extraction_id>/ > data/export.json`

```bash
python3 sdr.py facts data/export.json > queue/facts.json
```

## Step 2: qualify and write

Read `ICP.md` again, then write `queue/sdr.json`: one entry per lead in `facts.json`.

- Every lead: `{"id", "score", "reason"}`. Score 1 to 5 by the ICP, size rule first. The reason is one line, from the facts.
- A fit (3 or more) with a `safe` email and no "do not send" in `email_check`: add `"hook"`, `"subject"`, `"body"` and `"followup"`.
- A fit without a safe email: add `"skip": true`. The reason says why.
- The follow-up gives one new angle. It never repeats a sentence of the first email.

```bash
python3 sdr.py check queue/facts.json queue/sdr.json
```

Fix every `FAIL` and run it again.

## Step 3: approval

```bash
python3 sdr.py sheet queue/facts.json queue/sdr.json --max 20 > queue/queue.csv
```

`--max` is the daily cap in `ICP.md`. Rows are sorted best fit first; sequences over the cap say so and wait for the next run. Put the sheet where the user reviews: a Google Sheet when the session has a Google Drive tool, otherwise the CSV path. Point out the rows with an `Email check` note. Ask them to edit what they want and write `yes` in `Send (yes/no)`. Wait.

## Step 4: load the approved sequences into Instantly

1. The campaign needs two steps (`{{ai_subject}}` / `{{personalization}}`, then `{{ai_followup}}`) and stop on reply on, as in `docs/instantly.md`. Ask for its id.
2. Load the keys into the shell (`set -a; . ./.env; set +a`), then dry run: `python3 sdr.py push queue/queue.csv --campaign <id>`. It refuses a campaign without stop on reply, without stop for the company, or without the three variables, and it skips rows over the daily cap.
3. On a yes: `python3 sdr.py push queue/queue.csv --campaign <id> --send`. A person who is already in this campaign or in another one is skipped and named.
4. Ask the user to open the campaign, preview two or three leads, attach their sending accounts and launch it themselves.

## Step 5: every week

Offer `save_search`, then `create_recurring_export` on it (weekly). Each run returns only the people who are new to the search, so the SDR never pays twice for the same person. Each run spends credits; say so before creating it. Then run steps 2 to 4 on each new export, or connect the n8n version (`docs/n8n.md`) so each run arrives by webhook.
