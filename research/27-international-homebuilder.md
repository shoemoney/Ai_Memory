# 27. International homebuilder: CRM, phone and contractor agreements on a local AI stack

Research date: 2026-11-20. Scope: what a multi-country homebuilder needs when it replaces its CRM, phone system and paper contractor-agreement process with self-hosted, open-weight models and local memory. Every fact carries a source URL. Items marked UNVERIFIED were not confirmed from a primary source in this pass. Not legal advice: rules are quoted for their technical requirements.

## 1. The business and its data

A homebuilder runs several linked record sets, each with its own retention and access rules:

- **Land and lots**: parcels, option agreements, entitlement status, plats.
- **Communities / projects**: phases, plans (floor plans, elevations), budgets, draw schedules.
- **Home buyers**: lead, reservation, purchase contract, option and change-order selections, closing, warranty claims. This is personal data for the whole lifecycle.
- **Subcontractors and trades**: bids, contractor agreements, scopes of work (SOW), licences, insurance certificates that expire, lien waivers, payment draws, punch lists, inspection results.
- **Schedules** and site photos, which are the evidence base for disputes.

Vendor products model most of this. Procore's own pricing page describes "annual contracts" with "fixed, predictable pricing" and points to estimates for specific plans ([Procore pricing](https://www.procore.com/pricing)). Third-party estimates put Procore at roughly $25K to $200K+ a year for mid-size GCs ([Constructable, Jul 2026](https://constructable.ai/blog/procore-reviews-pricing-alternatives)); a different estimate gives $15K to $30K for a small GC ([OneCrew, Oct 2026](https://www.getonecrew.com/post/procore-pricing)). Figures from aggregators disagree, so treat them as UNVERIFIED for planning.

## 2. What they use today and what it costs

| Product | Pricing model (vendor source) | Figures found |
|---|---|---|
| Procore | Annual contract, volume-based, quote only | Vendor page gives no list price ([procore.com/pricing](https://www.procore.com/pricing)). Third-party: $25K-$200K+/yr ([Constructable](https://constructable.ai/blog/procore-reviews-pricing-alternatives)) |
| Buildertrend | Tailored quote after a sales call; "one-price-fits-all" is not used ([buildertrend.com/construction-software-pricing](https://buildertrend.com/construction-software-pricing/)) | Third-party estimates $339 to $1,099/month ([OneCrew, Aug 2026](https://www.getonecrew.com/post/buildertrend-pricing)); another reports $299 / $499 / $900+ per month tiers ([Toricent](https://toricentlabs.com/blog/buildertrend-pricing-2026.html)), UNVERIFIED against the vendor |
| Fieldwire (Hilti) | Per user | Pro from $39/user/month annual, Business $64 ([Fieldwire, Oct 2026](https://www.fieldwire.com/blog/procore-pricing/)), a vendor blog quoting its own list |
| Salesforce | Per user per tier | Starter Suite $25/user/month ([Salesforce](https://www.salesforce.com/pricing/is-salesforce-affordable/)); top AI tier about $550/user per a third party ([MarketBetter, Jun 2026](https://marketbetter.ai/blog/salesforce-sales-cloud-pricing-breakdown-2026/)) |
| HubSpot | Per seat | Sales Hub Revenue Hub Professional $57/seat/month on the vendor page ([hubspot.com/pricing/sales](https://www.hubspot.com/pricing/sales)); Starter about $15/seat annual per a third party (UNVERIFIED) |
| RingCentral | Per user | RingEX $20 to $35/user/month billed annually, $30 to $45 monthly, per third parties ([Nextiva](https://www.nextiva.com/blog/ringcentral-pricing.html), [Carly](https://www.usecarly.com/blog/ringcentral-pricing/)); AI add-ons and texting fees extra |

Consequence for planning: the cost being replaced is per-seat CRM plus per-user telephony plus construction-platform licences. A local stack swaps those for hardware, staff time and an accountable ops role. Vendor pages mostly withhold list prices, so the cost model should be built from quotes.

## 3. Digital contractor agreements

**US.** ESIGN (15 U.S.C. 7001) gives a general rule that a signature, contract or record relating to a transaction "may not be denied legal effect" because it is electronic ([NCUA summary](https://ncua.gov/regulation-supervision/manuals-guides/federal-consumer-financial-protection-guide/compliance-management/deposit-regulations/electronic-signatures-global-and-national-commerce-act-e-sign-act); [Williams Mullen](https://www.williamsmullen.com/insights/news/legal-news/what-are-rules-governing-use-electronic-signatures)). ESIGN section 7001 is a federal rule. Consent to conduct business electronically is required. UETA, the state uniform act, adds the criteria of intent to sign, consent, association of the signature with the record, and record retention ([Adobe overview](https://www.adobe.com/acrobat/business/hub/difference-between-esign-act-vs-ueta.html)). Full-text UETA adoption by state was not re-checked (UNVERIFIED).

**EU.** eIDAS Article 25(1): an electronic signature "shall not be denied legal effect and admissibility as evidence" merely because it is electronic or not qualified ([European Commission eSignature FAQ](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/880312429/eSignature+FAQ)). Advanced signatures (Article 26) must be uniquely linked to the signatory, capable of identifying them, and under their sole control ([TeamSync summary](https://www.teamsync.com/compliance/eidas-qes); secondary, the regulation text was not fetched). Qualified signatures carry the legal effect of a handwritten one. The eIDAS 2 EUDI wallet: every Member State must offer at least one certified wallet by December 2026 ([Internet of Trust](https://www.internetoftrust.com/regulations/eidas-2-eudi-wallet/)). The wallet is a signing and identity option, not a requirement to use it.

**UK.** Electronic Communications Act 2000 section 7: an electronic signature and its certification are "admissible in evidence" on authenticity questions ([legislation.gov.uk](https://www.legislation.gov.uk/ukpga/2000/7/section/7)). The explanatory notes leave weight to the court ([explanatory notes](https://www.legislation.gov.uk/ukpga/2000/7/notes/division/6/2/1)).

**Canada.** The Uniform Electronic Commerce Act is model law adopted by provinces and territories ([Government of Canada guidance](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/identity-credential-access-management/government-canada-guidance-using-electronic-signatures.html)). Province-by-province check required.

**Mexico.** NOM-151-SCFI-2016 sets requirements for electronic signatures and data messages, including conservation of data messages ([CEPAL](https://repositorio.cepal.org/bitstreams/de8803f3-a1f3-4fce-9317-1b08a9162639/download)). Full requirements UNVERIFIED.

**UAE.** Federal Decree-Law 46/2021 on Electronic Transactions and Trust Services; Article 18 covers the admissibility of electronic evidence and trust services ([TDRA copy](https://tdra.gov.ae/-/media/About/Trust-Services/Laws-and-regulations/Federal-Decree-Law-No-46-OF-2021-On-Electronic-Transactions-and-Trust-Services-EN.ashx)).

**What the self-hosted signing system must record.** Across these regimes the common technical record is: explicit intent to sign (a distinct action), consent to electronic dealing, signer identity evidence and the method used, a link between signature and record, the exact document hash at signing, a tamper-evident audit trail, a trusted timestamp, and retention. The EU rules add a signature level per document.

**Open-source self-hostable tools (verified in this pass):**
- **Documenso**: AGPL-3.0 Community Edition, free and self-hostable, with a commercial Enterprise Edition that removes AGPL source-disclosure ([Documenso licences](https://docs.documenso.com/docs/policies/licenses); [self-hosting](https://docs.documenso.com/docs/self-hosting)). Its enterprise tier includes SSO and AES/QES signing via CSC (per a third-party review, UNVERIFIED version).
- **DocuSeal**: open-source self-hosted option ([on-premises page](https://www.docuseal.com/on-premises); [GitHub](https://github.com/docusealco/docuseal)); a third-party listing shows about 19k GitHub stars. Licence and current release not verified from the repo page (UNVERIFIED).
- **OpenSign**: compared in 2026 reviews but licence and version not verified from a primary source (UNVERIFIED).

**Templates and clause libraries.** No primary source for a specific clause-library product was checked. The architectural requirement is to version templates and bind each signed instance to a template version hash.

**Document types usually not signable electronically.** This is jurisdiction-specific and was not verified in this pass. Common exclusions in these statutes include wills and some family-law instruments and certain real-property conveyances. Treat "lien waiver", "deed", "notarised" and "statutory notice" as needing a per-jurisdiction check (UNVERIFIED).

## 4. International operation

**Data-protection regimes.**
- **EU GDPR** Article 44: transfers outside the EU are allowed only under the chapter V conditions ([gdpr-info.eu Art. 44](https://gdpr-info.eu/art-44-gdpr/); body text not retrieved, UNVERIFIED beyond the article title).
- **UK GDPR**: the EU renewed UK adequacy on 19 December 2025, running to 27 December 2031 ([Bratby](https://bratby.law/uk-adequacy-decision-inbound-eu-to-uk-transfers/); [EUR-Lex Implementing Decision (EU) 2025/2574](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ%3AL_202502574)). The ICO maintains its own transfer guidance ([ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/)).
- **UAE PDPL** (Federal Decree-Law 45/2021): personal data may be transferred where a proper protection level is available ([UAE legislation](https://uaelegislation.gov.ae/en/legislations/1972/download); [trade.gov](https://www.trade.gov/market-intelligence/united-arab-emirates-allows-cross-border-data-flows-personal-data)).
- **Mexico**: a new Federal Law on Protection of Personal Data Held by Private Parties was published in the Diario Oficial on 20 March 2025 ([Diputados](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_orig_20mar25.pdf); [GT Law](https://www.gtlaw.com/es/insights/2025/3/nueva-ley-general-proteccion-de-datos)). Transfer rules UNVERIFIED.
- **Brazil LGPD**: not checked in this pass (UNVERIFIED).

**Residency design.** Per-region deployment is the simplest compliant shape: buyer and contractor personal data stays in the region of the project unless a transfer mechanism is documented. Only aggregate, de-identified metrics go to a central view.

**Languages and currency.** Multilingual coverage of open-weight models: Qwen3 lists 119 languages and dialects ([Qwen3 report](https://huggingface.co/papers/2505.09388)); Qwen3.5 lists 201 languages and dialects, up from 119 ([Alibaba](https://www.alibabagroup.com/document-1960233590314762240); [Qwen3.5 blog](https://qwen.ai/blog?id=qwen3.5)). Gemma 3 lists over 140 languages ([Hugging Face Gemma 3 blog](https://huggingface.co/blog/gemma3)); Gemma 4 is listed at 140+ languages with 128K context ([Google Gemma docs](https://ai.google.dev/gemma/docs)). Language count is not translation quality. A per-language translation eval on construction terms (lien, punch list, change order) is required before any model is trusted for contract text, and no such benchmark was verified here (UNVERIFIED). Currency and time-zone handling are application logic, not model logic.

## 5. Phone system

- **Asterisk**: current LTS lines named as Asterisk 22 and 23 by a third-party distribution ([Nerd Vittles, May 2026](https://nerdvittles.com/introducing-incredible-pbx-2026-for-debian-13/)); the official version page was blocked (UNVERIFIED for version details). FreePBX 17 is the current FreePBX generation per the Asterisk downloads page ([asterisk.org](https://www.asterisk.org/downloads/)).
- **FreeSWITCH**: CISA added FreeSWITCH CVE-2026-116779 (SignalWire FreeSWITCH code injection) to the Known Exploited Vulnerabilities catalogue on 9 November 2026 ([CISA alert](https://www.cisa.gov/news-events/alerts/2026/11/09/cisa-adds-four-known-exploited-vulnerabilities-catalog); from search snippet, page body not fetched). Patch level is a gating item, not a detail.
- **3CX**: simultaneous-call (SC) licensing with hosting charged separately ([3CX pricing](https://www.3cx.com/ordering/pricing/); page returned 403 in this pass, snippet text only). Not per-user.
- **SIP trunks per country**: carrier choice is per country and not researched here (UNVERIFIED).

**Call recording consent.** The US uses one-party and all-party consent by state. The UK and EU do not use that split; GDPR governs personal data across all 27 Member States ([JustCall, Sep 2026](https://justcall.io/blog/call-recording-laws-by-country-2026.html); [tldv](https://tldv.io/blog/call-recording-laws/)). Industry guides advise defaulting to the strictest law when any party is in an all-party jurisdiction ([Exporb](https://exporb.com/blog/en/global-call-recording-laws)). These are secondary sources; ICO and national DPA guidance was not fetched (UNVERIFIED).

**AI call handling.** EU AI Act Article 50 requires providers to design AI systems that interact directly with people so the person is informed they are dealing with an AI ([Article 50 text](https://artificialintelligenceact.eu/article/50/)). Transparency obligations applied from 2 August 2026 ([Morgan Lewis, Aug 2026](https://www.morganlewis.com/blogs/sourcingatmorganlewis/2026/08/eu-ai-acts-transparency-rules-what-went-into-effect-on-2-august)). The Digital Omnibus on AI (Regulation (EU) 2026/1744, published 24 July 2026) defers high-risk obligations ([CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/)). A reception bot is therefore a transparency case now, and a high-risk case only if it does more than route calls (UNVERIFIED for the exact classification).

## 6. Scale and hardware

**Sizing (estimate, not sourced).** A few hundred staff plus thousands of contractors and buyers implies on the order of a few hundred concurrent calls at peak across all sites, a few thousand active documents per day, and tens of thousands of emails per day. These are assumptions to be measured on the existing systems, not sourced figures.

**GPUs.** NVIDIA lists the RTX PRO 6000 Blackwell Server Edition with 96 GB GDDR7 ([NVIDIA](https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/)). TechPowerUp gives a launch price of $8,565 for the Workstation Edition ([TechPowerUp](https://www.techpowerup.com/gpu-specs/rtx-pro-6000-blackwell-workstation.c4272)); Server Edition price not verified (UNVERIFIED). Reseller listings exist but were not used as price sources.

**Shared serving.** vLLM's V1 scheduler enables chunked prefill by default where possible; it prioritises decode requests and batches prefills into the `max_num_batched_tokens` budget, with smaller values favouring inter-token latency and larger values time-to-first-token ([vLLM Optimization and Tuning](https://docs.vllm.ai/en/latest/configuration/optimization/)). Continuous batching is the scheduling pattern that lets many users share one server; a 2026 engineering explainer describes it as iteration-level scheduling ([Tianpan, Apr 2026](https://tianpan.co/blog/2026/04/09/continuous-batching-llm-inference), secondary). Per-region servers, each serving its own users, fit the residency rule above.

## 7. LLM memory needs for this business

- **Per-project and per-contractor memory**: facts with a validity interval (licence expiry, insurance certificate expiry, a sub's rate on a date). Store as dated rows, not as prose the model re-summarises.
- **Document memory over contracts and drawings**: the model must cite section, page and version. Multimodal input is needed for plans and site photos; Gemma 4 lists image and audio input ([Google Gemma docs](https://ai.google.dev/gemma/docs)); Qwen3.5 is described as natively multimodal ([Qwen3.5 blog](https://qwen.ai/blog?id=qwen3.5)).
- **Auditable facts**: who agreed to what, when, which document version and hash. This is an append-only event log; the model is a reader, not the system of record.
- **Cross-border isolation**: memory stores are partitioned by jurisdiction, with no cross-region retrieval of personal data.
- **Shared team memory**: project-level facts visible to permitted staff only, with access logged.
- **Must never be decided by a model**: contract acceptance and signature, payment release, lien-waiver sufficiency, licence or insurance validity determination, and any change to a recorded legal fact. The model drafts, flags and routes; a deterministic rule and a named human decide.

## Architectural consequences

1. Keep the record of signature in a deterministic signing service with hash, timestamp and identity evidence, not in model memory. Basis: ESIGN/UETA intent-and-record criteria ([Adobe](https://www.adobe.com/acrobat/business/hub/difference-between-esign-act-vs-ueta.html)) and eIDAS Article 25 ([EC FAQ](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/880312429/eSignature+FAQ)).
2. Choose the signature level per document type and jurisdiction; eIDAS QES is a per-document decision. Basis: eIDAS Article 26 summary ([TeamSync](https://www.teamsync.com/compliance/eidas-qes)).
3. Pick Documenso (AGPL-3.0) or verify DocuSeal's licence before any modification is shipped, since AGPL obliges source disclosure for network use. Basis: [Documenso licences](https://docs.documenso.com/docs/policies/licenses).
4. Partition data per region: EU, UK, UAE and Mexico stores separated, with transfers documented. Basis: GDPR Art. 44 ([gdpr-info](https://gdpr-info.eu/art-44-gdpr/)), UAE PDPL ([UAE](https://uaelegislation.gov.ae/en/legislations/1972/download)).
5. Default to strictest recording consent and announce recording and AI at call start. Basis: [JustCall](https://justcall.io/blog/call-recording-laws-by-country-2026.html); EU AI Act Article 50 ([text](https://artificialintelligenceact.eu/article/50/)).
6. Treat FreeSWITCH and Asterisk patching as a release gate. Basis: CISA KEV entry ([CISA](https://www.cisa.gov/news-events/alerts/2026/11/09/cisa-adds-four-known-exploited-vulnerabilities-catalog)).
7. Validate open-weight translation per language on construction terms before use. Basis: language counts only ([Qwen3.5](https://qwen.ai/blog?id=qwen3.5), [Gemma docs](https://ai.google.dev/gemma/docs)); no translation benchmark verified.
8. Size GPU servers per region and rely on continuous batching with chunked prefill. Basis: [vLLM docs](https://docs.vllm.ai/en/latest/configuration/optimization/).
9. Store validity-dated facts (licences, insurance, rates) as rows with effective dates, and keep decisions outside the model. Basis: the requirements in section 7, no external source beyond the regimes above.

## Sources

- Procore pricing: https://www.procore.com/pricing
- Constructable, Procore 2026: https://constructable.ai/blog/procore-reviews-pricing-alternatives
- OneCrew, Procore 2026: https://www.getonecrew.com/post/procore-pricing
- Buildertrend pricing page: https://buildertrend.com/construction-software-pricing/
- OneCrew, Buildertrend 2026: https://www.getonecrew.com/post/buildertrend-pricing
- Toricent, Buildertrend 2026: https://toricentlabs.com/blog/buildertrend-pricing-2026.html
- Fieldwire, Procore pricing: https://www.fieldwire.com/blog/procore-pricing/
- Salesforce affordability: https://www.salesforce.com/pricing/is-salesforce-affordable/
- MarketBetter, Salesforce 2026: https://marketbetter.ai/blog/salesforce-sales-cloud-pricing-breakdown-2026/
- HubSpot Sales pricing: https://www.hubspot.com/pricing/sales
- Nextiva, RingCentral 2026: https://www.nextiva.com/blog/ringcentral-pricing.html
- Carly, RingCentral 2026: https://www.usecarly.com/blog/ringcentral-pricing/
- NCUA, ESIGN: https://ncua.gov/regulation-supervision/manuals-guides/federal-consumer-financial-protection-guide/compliance-management/deposit-regulations/electronic-signatures-global-and-national-commerce-act-e-sign-act
- Williams Mullen, e-signature rules: https://www.williamsmullen.com/insights/news/legal-news/what-are-rules-governing-use-electronic-signatures
- Adobe, ESIGN vs UETA: https://www.adobe.com/acrobat/business/hub/difference-between-esign-act-vs-ueta.html
- European Commission eSignature FAQ: https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/880312429/eSignature+FAQ
- TeamSync, eIDAS QES: https://www.teamsync.com/compliance/eidas-qes
- Internet of Trust, eIDAS 2: https://www.internetoftrust.com/regulations/eidas-2-eudi-wallet/
- legislation.gov.uk, ECA 2000 s.7: https://www.legislation.gov.uk/ukpga/2000/7/section/7
- ECA 2000 explanatory notes: https://www.legislation.gov.uk/ukpga/2000/7/notes/division/6/2/1
- Government of Canada, e-signature guidance: https://www.canada.ca/en/government/system/digital-government/online-security-privacy/identity-credential-access-management/government-canada-guidance-using-electronic-signatures.html
- CEPAL, NOM-151: https://repositorio.cepal.org/bitstreams/de8803f3-a1f3-4fce-9317-1b08a9162639/download
- UAE Decree-Law 46/2021 (TDRA copy): https://tdra.gov.ae/-/media/About/Trust-Services/Laws-and-regulations/Federal-Decree-Law-No-46-OF-2021-On-Electronic-Transactions-and-Trust-Services-EN.ashx
- Documenso licences: https://docs.documenso.com/docs/policies/licenses
- Documenso self-hosting: https://docs.documenso.com/docs/self-hosting
- DocuSeal on-premises: https://www.docuseal.com/on-premises
- DocuSeal GitHub: https://github.com/docusealco/docuseal
- GDPR Art. 44: https://gdpr-info.eu/art-44-gdpr/
- EUR-Lex 2025/2574: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ%3AL_202502574
- Bratby, UK adequacy: https://bratby.law/uk-adequacy-decision-inbound-eu-to-uk-transfers/
- ICO international transfers: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/
- UAE PDPL text: https://uaelegislation.gov.ae/en/legislations/1972/download
- trade.gov, UAE data flows: https://www.trade.gov/market-intelligence/united-arab-emirates-allows-cross-border-data-flows-personal-data
- Mexico LFPDPPP (2025): https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_orig_20mar25.pdf
- JustCall, call recording 2026: https://justcall.io/blog/call-recording-laws-by-country-2026.html
- tldv, call recording: https://tldv.io/blog/call-recording-laws/
- Exporb, call recording: https://exporb.com/blog/en/global-call-recording-laws
- Nerd Vittles, Asterisk/FreePBX 2026: https://nerdvittles.com/introducing-incredible-pbx-2026-for-debian-13/
- asterisk.org downloads: https://www.asterisk.org/downloads/
- CISA KEV alert, 9 Nov 2026: https://www.cisa.gov/news-events/alerts/2026/11/09/cisa-adds-four-known-exploited-vulnerabilities-catalog
- 3CX pricing: https://www.3cx.com/ordering/pricing/
- EU AI Act Article 50: https://artificialintelligenceact.eu/article/50/
- Morgan Lewis, Article 50 in effect: https://www.morganlewis.com/blogs/sourcingatmorganlewis/2026/08/eu-ai-acts-transparency-rules-what-went-into-effect-on-2-august
- CSA research note, Digital Omnibus: https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/
- NVIDIA RTX PRO 6000 Server Edition: https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/
- TechPowerUp RTX PRO 6000: https://www.techpowerup.com/gpu-specs/rtx-pro-6000-blackwell-workstation.c4272
- vLLM Optimization and Tuning: https://docs.vllm.ai/en/latest/configuration/optimization/
- Tianpan, continuous batching: https://tianpan.co/blog/2026/04/09/continuous-batching-llm-inference
- Qwen3 technical report: https://huggingface.co/papers/2505.09388
- Qwen3.5 blog: https://qwen.ai/blog?id=qwen3.5
- Alibaba, Qwen3.5: https://www.alibabagroup.com/document-1960233590314762240
- Gemma 3 (Hugging Face blog): https://huggingface.co/blog/gemma3
- Google Gemma docs: https://ai.google.dev/gemma/docs

**Not verified in this pass:** Buildertrend and HubSpot list prices from vendor pages; 3CX and Asterisk version pages (403); OpenSign licence and version; DocuSeal licence and release; Mexico NOM-151 and UAE/Canada statutory text beyond summaries; UETA state adoption; which document types are unsignable per jurisdiction; Brazil LGPD; ICO call-recording guidance; any translation-quality benchmark for open-weight models on construction terms; Server Edition GPU price; SIP trunk carriers.
