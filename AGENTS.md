# Agent instructions

This repo is an AI SDR agent. It watches a Sales Navigator search for a buying signal (people who just started a sales leadership role), exports the new people with Evaboot, scores each one against the ICP, writes a two-email sequence for the ones that fit, queues them in a sheet for the user to approve, and loads the approved ones into an Instantly campaign that stops on reply. The user launches the campaign; the agent never sends an email. When the user asks for an AI SDR, to automate outbound prospecting, or to run their SDR work with AI:

1. Follow the skill in `skills/ai-sdr/SKILL.md` step by step.
2. Read `ICP.md` for who fits, the offer, the sequence rules and the daily cap. If it says `Status: EXAMPLE`, ask the user and update it.
3. Use `sdr.py` for the facts, the checks, the sheet and the Instantly push. The Evaboot MCP server does the Sales Navigator work (`.mcp.json`).
4. If the user is not connected yet, follow `docs/connect-your-agent.md` with them. For the Instantly campaign, follow `docs/instantly.md`.
5. If the user wants n8n instead, follow `docs/n8n.md` with them one step at a time: you cannot click inside n8n, so say exactly what to do and wait for their confirmation.

Confirm with the user before every export (1 Evaboot credit per lead), before creating a recurring export, and before `sdr.py push --send`. Never launch a campaign and never send an email. Never ask for or handle an API key: the user writes them into `.env`. Never commit `.env`, `data/` or `queue/`: they hold real people's data.
