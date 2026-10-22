# Who your AI SDR contacts, what it says, and when it stops

Status: EXAMPLE. Your agent asks you and replaces this line with "Status: yours" once the file is yours.

## The signal

The search the agent watches: people who **started a sales leadership role in the last 90 days** (Sales Navigator's "Changed jobs" filter). A new sales leader rebuilds the pipeline and the prospect lists in the first months.

## Fit: score every lead from 1 to 5

Apply the size rule first: over 1,000 employees is a 2, whatever the role.

- **5**: owns the pipeline or the people who build it (VP Sales, Head of Sales, CRO, Head of Inside Sales or SDRs, Head of RevOps) at a B2B software company of 50 to 1,000 employees, with a sales team of 10 or more, or company growth over 20% in a year.
- **4**: the same role with a smaller team (3 to 9 sellers), or a B2B company that is not software.
- **3**: worth a try: a company under 50 employees, a role one step away from the pipeline (commercial operations), or a business unit of under 1,000 people inside a larger group.
- **2**: do not contact: a company over 1,000 employees, whatever the role (a procurement process, not an SDR email), partnerships, B2C.
- **1**: do not contact: M&A, investors, fractional or consulting roles, founders of a company under 10 people, nobody in the role.

The agent writes the reason in one line from the facts. Only 3 and above get a sequence.

## The offer

- **Product:** Evaboot exports a LinkedIn Sales Navigator search to a clean spreadsheet, with verified professional emails.
- **For:** sales leaders who build or rebuild their team's prospect lists.
- **Why it matters to them:** clean lists with emails in minutes instead of manual copy-paste, and fewer bounces. A saved search can export new leads every week.
- **Proof you may use:** none beyond the product facts above. Never invent customers, numbers or results.
- **Ask:** a low-effort question, for example "Worth a look?". Never a 30-minute meeting in the first email.

## The sequence

1. **Email 1:** subject of 60 characters at most, lower case. Body of 40 to 110 words: "Hi <first name>,", one short paragraph on them (the hook), one on the offer, one line for the ask. No link.
2. **Follow-up, 3 days later in the same thread:** 20 to 70 words. One new thing (a different use, a different angle), never "just following up". No link.
3. **Stop:** the moment the person answers, or anyone at their company answers. The campaign must have both settings on; `sdr.py push` refuses a campaign without stop on reply.

## Limits

- **20 new sequences a day at most** (`sdr.py sheet --max 20`). The rest wait in the sheet for the next run.
- Only `safe` emails, never an email on a link site such as linktr.ee.
- Nothing goes out before a person writes `yes` in the sheet.
