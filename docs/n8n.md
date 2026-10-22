# Run it in n8n

[`n8n/ai-sdr-agent.json`](../n8n/ai-sdr-agent.json) is the same SDR for n8n. An Evaboot recurring export of your signal search sends the new people to a webhook, Claude qualifies them and writes the sequences into your Google Sheet, and an approval form loads the rows you mark `yes` into Instantly.

## What runs

1. **New leads from Evaboot** (Webhook): each run of your recurring export posts its new leads here.
2. **Lead facts** (Code): the same facts and email-domain check as `sdr.py`.
3. **Qualify and write** (AI Agent with Claude): a 1-to-5 score and a reason for every lead, and a first email and a follow-up for each fit, by the ICP and offer in Your settings.
4. **Check, rank and cap** (Code): the same checks as `sdr.py check`, best fit first, and the daily cap.
5. **Add to the approval sheet** (Google Sheets).
6. **Load approved rows** (form): **Read the campaign** and stop if it does not stop on reply, **Read the sheet**, keep the rows marked `yes` with a `safe` email, **Add to Instantly**, and report who was skipped because they are already in a campaign.

## Set it up

1. **Set up the Instantly campaign** with [instantly.md](instantly.md) and copy its id.
2. **Make the sheet:** a Google Sheet with this header row:
   `Name, Title, Company, Fit (1-5), Why, Email, Email status, Email check, Hook, Subject, Email 1, Follow-up, Send (yes/no)`
3. **Import** the JSON in n8n: *Workflows > Import from file*.
4. **Add three credentials:**
   - **Anthropic** on the Claude node.
   - **Google Sheets** on both sheet nodes.
   - **Header Auth** named `Instantly API key`: name `Authorization`, value `Bearer <your Instantly API key>`. Select it on **Read the campaign** and **Add to Instantly**.
5. **Fill in both settings nodes** (Your settings and Approval settings): `sheet_url` (with its `gid`), `instantly_campaign_id`, `daily_cap`, `icp` and `offer`.
6. **Publish** the workflow and copy the production URL of **New leads from Evaboot**.
7. **Connect it in Evaboot:** in [Integrations](https://app.evaboot.com/dash/integrations/), add an n8n destination with that URL. Or ask your agent: "connect this n8n webhook and attach my recurring export to it".
8. **Create the recurring export** of your signal search (weekly or daily) and attach it to that destination.
9. **Test without waiting:** push any finished export to the destination from Evaboot (no credits). The rows appear in your sheet a minute later. Write `yes` on a few, open the **Load approved rows** form and submit it.

## Good to know

- Each run of a recurring export holds only the people who are new to the search, so the SDR never pays twice for the same person.
- An email on a link site such as linktr.ee is never loaded: the company's LinkedIn page lists that site as its website, so the email cannot be right.
- Nothing is sent. You preview the leads in Instantly and launch the campaign yourself.

Back to the [README](../README.md).
