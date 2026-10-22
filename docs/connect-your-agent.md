# Connect your agent by hand

The prompt in the README does all of this for you. These are the same steps, for when you want to do them yourself.

1. **Create your Evaboot account** at [dash.evaboot.com](https://dash.evaboot.com/accounts/signup/?last_click_origin=ai-sdr-agent-repo) and install the [Chrome extension](https://dash.evaboot.com/install/) to connect Sales Navigator. You need an active Sales Navigator seat.
2. **Get the repo:**
   ```bash
   git clone https://github.com/evaboot-labs/ai-sdr-agent.git
   cd ai-sdr-agent
   ```
3. **Add your keys.** Copy your Evaboot API key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/) and your Instantly API key (Settings > Integrations > API keys, API v2), then:
   ```bash
   cp .env.example .env          # paste the keys after EVABOOT_API_KEY= and INSTANTLY_API_KEY=
   export EVABOOT_API_KEY=...    # same Evaboot key, for your agent
   ```
4. **Connect the Evaboot MCP server:**
   - **Claude Code** reads `.mcp.json` in this folder and uses `EVABOOT_API_KEY` from your environment. Export the key before you start Claude Code: a session that is already open does not see it.
   - **Codex:** `codex mcp add evaboot --url https://mcp.evaboot.com/mcp --bearer-token-env-var EVABOOT_API_KEY`
   - **Cursor:** add `https://mcp.evaboot.com/mcp` with the header `Authorization: Bearer <your key>`.
   - **Claude or ChatGPT on the web:** add `https://mcp.evaboot.com/mcp` as a custom connector and sign in. The web apps cannot run `sdr.py`, so use Claude Code, Codex or Cursor for this repo, or the n8n version.
5. **Set up the Instantly campaign** with [instantly.md](instantly.md).
6. **Describe your buyers and your offer** in [`ICP.md`](../ICP.md), or let your agent ask you.
7. **Check** (Python 3.9+, no packages to install): `python3 sdr.py -h` lists the commands.

Then ask your agent: **"Run my AI SDR on new sales leaders."**

Back to the [README](../README.md).
