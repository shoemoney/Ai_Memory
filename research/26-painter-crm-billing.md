# Painter CRM and Billing: What a Small Crew Needs, What It Costs, and What a Local Assistant Can Replace

Research as of 2026-11-20. Every fact carries a source URL. Anything not verified is marked UNVERIFIED. Prices are US list prices from search snippets or vendor pages as noted; they move often.

## 1. The real workflow and data

A painting job moves through a fixed chain, and each step produces data the next step needs:

- **Lead.** Source (referral, Google Business, Nextdoor, website form, phone call, repaint list). Track source so you know which channel pays.
- **Site visit.** Rooms, surfaces (walls, ceilings, trim, doors, cabinets, exterior siding, soffits), approximate square footage, prep condition (cracks, peeling, mildew, drywall repair), access (ladders, gate codes, pets, parking).
- **Estimate.** Per-surface quantity, prep hours, number of coats, paint product and sheen, colour codes per room, material quantities, labour hours, markup, optional add-ons. Estimating apps model this as "production rates" and "material lists" (PaintScout lists production rates and material lists as core features, https://www.paintscout.com/pricing).
- **Proposal and acceptance.** Sent by email or text, e-signed, with a deposit request.
- **Scheduling and crew.** Dates, crew assignments, drive time, daily checklists.
- **Materials.** Paint purchased per job, returns, leftovers stored per job.
- **Change orders.** Added work (extra trim, rot repair, extra coat) that must be priced and approved in writing. Joist lists "add change orders" on its Elite tier (https://www.joist.com/pricing/).
- **Photos.** Before and after, per room, attached to the job. Joist's Pro tier includes "add line items and document photos" (https://www.joist.com/pricing/).
- **Invoice, deposit and payment.** Deposit at signing, progress or final invoice, card or ACH payment, late reminders.
- **Follow-up and reviews.** Unanswered quotes, review requests, referral asks.
- **Repeat work and repaint cycle.** Interior repaints are commonly planned by age and paint type; exterior is planned by climate. The record needed is "last painted, product, colour, coats, date."
- **Warranty notes.** Callbacks for peeling, touch-ups, and what was promised.

The key data is the per-room colour record (brand, colour name and code, sheen, coats) and the job history per customer. Those are the two things a generic CRM handles badly for painters and the two things a notes-based assistant handles well.

## 2. Paid tools painters use now (list prices, as of Nov 2026)

| Tool | Plans and price | Source |
|---|---|---|
| **Jobber** | Core, Connect, Grow, Plus. Site states "plans from $29 to $529/mo (billed annually)"; FAQ snippet gives $29 Core, $99 Connect, $149 Grow, $399 Plus starting at five users. Vendor page fetch was blocked (403), so these come from snippets. | https://www.getjobber.com/pricing/ ; https://www.getjobber.com/faq/ (snippet) |
| **Housecall Pro** | Basic, Essentials, MAX. Third-party aggregators (Nov 2026) list $59 / $149 / $299 per month billed annually, with 1, 5 and 8 users; monthly prices are higher. Vendor page fetch returned only navigation, so vendor figures are UNVERIFIED on the primary page. | https://unstack.us/blog/housecall-pro-pricing ; https://www.housecallpro.com/pricing/ |
| **Joist** | Basics $10/mo monthly or $8.34/mo annual; Pro $17 / $14.17; Elite $32 / $26.67; Run $70 / $58.33 (intro offer). 14-day free trial. Vendor page read directly. | https://www.joist.com/pricing/ |
| **PaintScout** | Sales (estimating, proposals, payments) $119/mo monthly or $99/mo annual. Operations add-on $99/mo monthly or $79/mo annual. Team seats $20/user/mo. Vendor page read directly. | https://www.paintscout.com/pricing |
| **QuickBooks Online** | Simple Start $38/mo (promo "70% off for 3 months" shown). Essentials $85, Plus $140, Advanced $340 per one third-party review dated Oct 2026. One NerdWallet snippet gives a range of $38 to $275, which conflicts; treat the top end as UNVERIFIED. | https://quickbooks.intuit.com/pricing/ ; https://eleven.run/blog/quickbooks-review |

A one-person painter on Joist Pro or Jobber Core is paying roughly $100 to $350 per year. A two-to-five-person crew on Jobber Connect or Housecall Pro Essentials pays roughly $1,200 to $1,800 per year before payment fees. Those are the numbers the guide should be replacing.

## 3. Open-source, self-hostable building blocks

**Invoicing.**
- **Invoice Ninja.** Licence: Elastic License 2.0, which allows internal commercial self-hosting but forbids offering it as a hosted service to others (https://www.opensourcealternatives.to/item/invoiceninja). A white-label licence is an optional paid add-on (WZ-IT quotes USD 40/yr for branding removal; https://wz-it.com/en/blog/invoiceninja-all-in-one-solution-invoicing/, dated Feb 2025, re-verify). Latest release visible on GitHub at check time: v5.13.56 (UNVERIFIED as current; read from a GitHub page link). Self-host docs: https://invoiceninja.github.io/docs/self-host/self-host-installation
- **Crater.** Licence: AGPL-3.0 (https://github.com/crater-invoice-inc/crater). Covers invoices and estimates. Current version and maintenance activity: UNVERIFIED; the GitHub release page was not readable in this pass.

**CRM.**
- **Twenty.** Licence: AGPL-3.0 (https://github.com/twentyhq/twenty/blob/main/LICENSE). Self-hosting needs four containers: app, worker, PostgreSQL, Redis (https://selfhost.dev/deploy/twenty/; docs at https://docs.twenty.com/developers/self-host/self-host). Release cadence per a third-party review: v2.0 in April 2026, with releases on Nov 5, 9 and 13, 2026 (https://www.taskrhino.ca/en-us/twenty-crm-implementation/twenty-crm-review/, UNVERIFIED against GitHub). The GitHub tag I could read was `sdk/v2.59.0`, which is an SDK tag, not the app version.
- EspoCRM and similar were not checked in this pass (UNVERIFIED).

**Is SQLite plus an agent realistic?** Plausibly yes for one person, and I found no primary source that settles it. My reasoning, not a sourced claim: a painter's data is small (a few hundred customers, a few thousand jobs), so one SQLite file with tables for customers, sites, rooms, colours, jobs, estimate lines, invoices and photos is enough. What you lose is the free invoice-to-payment flow and client-facing portal. The honest split is: SQLite for the record and the assistant's memory; Invoice Ninja or a payment processor for money moving. Treat this as a design judgement, UNVERIFIED as a tested claim.

## 4. What cannot be local

- **Card payments need a processor.** Stripe lists cards at 2.9% + 30 cents per successful charge for US standard pricing (https://stripe.com/pricing). Square lists in-person card-present at 2.6% + 15 cents on the free plan, and online at 2.9% + 30 cents (https://squareup.com/us/en/the-bottom-line/managing-your-finances/credit-card-processing-fees-and-rates ; https://www.nerdwallet.com/business/software/learn/square-fees). Stripe ACH is 0.8% capped at $5 per a third-party write-up (https://www.paycove.io/blog/stripe-payment-links; primary Stripe page not re-read).
- **Bank transfers and ACH** need a bank or processor. A local system can record them, not move them.
- **Text messages to customers** need a carrier-compliant route. Twilio's US long-code figure is $0.0083 per segment (per aggregators; the Twilio page itself was not re-read, so UNVERIFIED on the primary page: https://www.twilio.com/en-us/sms/pricing/us). US 10DLC registration applies to business texting; carriers enforce it (https://www.twilio.com/en-us/guidelines/us/sms). Alternatively, the painter sends from his own phone. The phone's own Messages app is free and needs no bridge.
- **Email delivery** needs an SMTP relay or provider. A home server sending mail directly is usually blocked or spam-filtered; use a relay and verify SPF/DKIM (UNVERIFIED in this pass; standard practice).
- **Sales tax on painting labour varies by state.** Avalara's state guide says services are taxed in most states but in different ways, and that rules change (https://www.avalara.com/us/en/learn/whitepapers/service-taxability-by-state.html). Examples from official sources: DC's Office of Tax and Revenue lists "real property maintenance" as taxable at 6% but excludes "painting" from that category (https://otr.cfo.dc.gov/page/taxable-and-non-taxable-services). Florida's sales-tax guidance on construction says charges for repairs needing only labour are not taxable (https://floridarevenue.com/forms_library/current/gt800067.pdf; read from search snippet, the full PDF timed out). Kansas Pub. KS-1525 says materials bought by contractors are taxable (https://www.ksrevenue.gov/pub1525.html). The point for the guide: the software must store taxable and non-taxable lines separately, and the painter's accountant decides the rule. No advice here.

## 5. What an LLM assistant actually does for this business

Each of these is a concrete task with a clear input and output:

- **Draft an estimate from notes and photos.** Input: "Living room 14x18, 9 ft ceiling, two coats, Sherwin-Williams Alabaster, trim semi-gloss, prep crack repair." Output: surface list, square feet, prep hours, coats, material quantity, labour hours, and a line-item draft. The painter checks it. Accuracy depends on the production-rate table the owner supplies; the assistant does arithmetic and wording, not judgement.
- **Remember each house.** Per-room colour codes, sheen, quirks ("gate code 4417, dog in back, use the south door"), what was promised under warranty. This is what a notes file and a database do together.
- **Chase unpaid invoices and unanswered quotes.** A scheduled query over open invoices and quotes, then a draft reminder for the owner to approve. Sending should stay a human click until trust is built.
- **Answer history questions.** "What did I charge for the last three exterior jobs?" is a query over the jobs table. This is where SQLite plus a small query tool beats a generic chat memory.
- **Prepare the day.** Pull today's jobs, drive order, crew, paint pickups, and open change orders into a one-page schedule.

**Practitioner anecdotes (labelled, snippet-level only; Reddit pages were not readable in this pass):**
- r/EntrepreneurRideAlong, May 2026: a user says PaintScout "handles estimating well, but scheduling is killing me" (https://www.reddit.com/r/EntrepreneurRideAlong/comments/1t5arz4/paintscout_handles_estimating_well_but_scheduling/). Anecdote, one user.
- r/estimators, June 2025: a thread asks "Anyone using AI for estimating?" and a commenter says they do not want a black-box estimate, only counting and accurate answers to questions they ask (https://www.reddit.com/r/estimators/comments/1lc2lmz/anyone_using_ai_for_estimating/). Anecdote, one commenter.
- Several r/estimators and r/Housepainting101 threads ask about estimating tools generally (https://www.reddit.com/r/estimators/comments/1l3544x/what_is_the_best_ai_estimator_assistant_for/). No local-model painter write-up was found. Claim that practitioners run local models for this: UNVERIFIED, none found.

## 6. Phone input to a home server

- **Messaging bridge.** Telegram's Bot API accepts photos and voice notes, and getFile retrieves them for a server-side agent (https://core.telegram.org/bots/api). The painter sends a photo and a voice note from his phone; the server transcribes, drafts, and replies. Works over the public internet with no open ports on the home network. Telegram is not end-to-end encrypted for bot chats; keep customer PII out of messages or accept that risk.
- **Private network.** Tailscale's Personal plan is free and permits up to 6 users in one tailnet (https://tailscale.com/docs/account/manage-plans/free-plans-discounts; pricing at https://tailscale.com/pricing). A small web app on the home server reached over the tailnet keeps all traffic private with no public exposure. WireGuard is the lower-level option (not re-verified in this pass).
- **Practical split.** Photos and voice via a bot for speed; a tailnet-only web page for the schedule, customer record and invoice view.

## Sources

- Jobber pricing: https://www.getjobber.com/pricing/ (403 on fetch; figures from search snippet), https://www.getjobber.com/faq/ (snippet)
- Housecall Pro pricing: https://www.housecallpro.com/pricing/ (partially read), https://unstack.us/blog/housecall-pro-pricing (aggregator)
- Joist pricing: https://www.joist.com/pricing/ (read directly)
- PaintScout pricing: https://www.paintscout.com/pricing (read directly)
- QuickBooks pricing: https://quickbooks.intuit.com/pricing/ (snippet); https://eleven.run/blog/quickbooks-review (third-party)
- Invoice Ninja: https://www.opensourcealternatives.to/item/invoiceninja ; https://www.invoiceninja.org/ ; https://invoiceninja.github.io/docs/self-host/self-host-installation
- Crater: https://github.com/crater-invoice-inc/crater
- Twenty: https://github.com/twentyhq/twenty/blob/main/LICENSE ; https://docs.twenty.com/developers/self-host/self-host ; https://selfhost.dev/deploy/twenty/
- Stripe: https://stripe.com/pricing (snippet)
- Square: https://squareup.com/us/en/the-bottom-line/managing-your-finances/credit-card-processing-fees-and-rates (snippet)
- Twilio: https://www.twilio.com/en-us/sms/pricing/us ; https://www.twilio.com/en-us/guidelines/us/sms
- Sales tax: https://www.avalara.com/us/en/learn/whitepapers/service-taxability-by-state.html ; https://otr.cfo.dc.gov/page/taxable-and-non-taxable-services ; https://floridarevenue.com/forms_library/current/gt800067.pdf ; https://www.ksrevenue.gov/pub1525.html
- Telegram Bot API: https://core.telegram.org/bots/api
- Tailscale: https://tailscale.com/pricing ; https://tailscale.com/docs/account/manage-plans/free-plans-discounts
- Anecdotes: https://www.reddit.com/r/EntrepreneurRideAlong/comments/1t5arz4/paintscout_handles_estimating_well_but_scheduling/ ; https://www.reddit.com/r/estimators/comments/1lc2lmz/anyone_using_ai_for_estimating/ ; https://www.reddit.com/r/estimators/comments/1l3544x/what_is_the_best_ai_estimator_assistant_for/

## Could not verify

- Jobber and Housecall Pro primary pricing pages (blocked or truncated); figures are snippet or aggregator.
- Current versions of Crater and Twenty's app release (GitHub release pages not readable; Twenty's tag read was an SDK tag).
- Twilio and Stripe primary numbers beyond the snippets; QuickBooks top-tier price conflict.
- Local-model practitioner write-ups for painters: none found; Reddit bodies not readable.
- SQLite-plus-agent viability for this use: design judgement, not tested.
