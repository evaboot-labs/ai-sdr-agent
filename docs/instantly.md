# Set up the Instantly campaign

The agent adds each approved lead to an Instantly campaign with three fields: the first email's body in `personalization`, its subject in the custom variable `ai_subject`, and the follow-up in `ai_followup`. The campaign sends them as a two-step sequence.

1. In Instantly, create a campaign.
2. In **Sequences**:
   - Step 1: subject `{{ai_subject}}`, body `{{personalization}}`. Nothing else: the AI wrote the whole email.
   - Step 2, 3 days later: leave the subject empty (it goes in the same thread) and set the body to `{{ai_followup}}`.
3. In **Options**, turn on **Stop sending emails on reply** and **Stop campaign for company on reply**. `sdr.py push` refuses a campaign without both.
4. Set a **daily limit** that matches the cap in `ICP.md`.
5. Copy the campaign id from the address bar (`app.instantly.ai/app/campaign/<id>/...`).
6. Put your Instantly API key in `.env` as `INSTANTLY_API_KEY` (Settings > Integrations > API keys, API v2), and load it into your shell before a push: `set -a; . ./.env; set +a`.
7. Run the dry run, then the push with `--send` (see the skill, step 4).
8. Open the campaign, preview a few leads to read the real emails, attach your sending accounts, and launch.

Only leads with an Evaboot email status of `safe` are pushed, never an email on a link-site domain such as linktr.ee, and never a person who is already in another campaign.

Back to the [README](../README.md).
