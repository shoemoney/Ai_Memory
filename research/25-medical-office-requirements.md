# 25. Medical office requirements for a locally run practice system (as of 2026-11-20)

Engineering research, not legal advice. Rule text is quoted from the sources listed at the end. Anything not verified in this session is marked **UNVERIFIED**.

## 1. HIPAA Security Rule: technical and administrative safeguards

### 1a. Technical safeguards (45 CFR 164.312)

Verbatim from the Cornell LII copy of 164.312 (eCFR itself blocked automated fetches this session):

- **Access control (a)(1):** "Implement technical policies and procedures for electronic information systems that maintain electronic protected health information to allow access only to those persons or software programs that have been granted access rights." This explicitly covers software programs, so an LLM agent is in scope as an accessor.
- **Unique user identification (a)(2)(i), Required:** "Assign a unique name and/or number for identifying and tracking user identity." A shared "front desk" login or a shared service account for the AI layer does not satisfy this.
- **Emergency access (a)(2)(ii), Required:** procedures for obtaining ePHI during an emergency.
- **Automatic logoff (a)(2)(iii), Addressable:** "terminate an electronic session after a predetermined time of inactivity." Applies to staff consoles and to any long-lived agent session that displays PHI.
- **Encryption and decryption (a)(2)(iv), Addressable.**
- **Audit controls (b), Standard:** "record and examine activity in information systems that contain or use electronic protected health information."
- **Integrity (c)(1) and authentication of ePHI (c)(2), Addressable.**
- **Person or entity authentication (d), Standard:** "verify that a person or entity seeking access to electronic protected health information is the one claimed."
- **Transmission security (e)(1)-(2):** integrity controls and encryption "whenever deemed appropriate" (Addressable).

Architectural reading: every one of these applies to the store, the agent, and the phone/SMS path, whether or not the model is local.

### 1b. Administrative points that shape architecture (45 CFR 164.308)

- **Risk analysis (a)(1)(ii)(A), Required:** "Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of electronic protected health information."
- **Risk management (a)(1)(ii)(B), Required**, and **information system activity review (a)(1)(ii)(D), Required:** "regularly review records of information system activity, such as audit logs, access reports, and security incident tracking reports." An audit trail nobody reads does not meet this.
- **Access establishment and modification (a)(4)(ii)(C), Addressable**, and termination procedures (a)(3)(ii)(C).
- **Contingency plan (a)(7)(i), Standard**, with **Required** implementation specs: data backup plan (A), disaster recovery plan (B), and emergency mode operation plan (C). Testing and applications/data criticality analysis are Addressable (D, E). For a local system this means a tested restore from backup and a documented way to run the front desk when the box is down. Phone and scheduling must keep working in that mode.
- **Business associate contracts (b)(1):** a covered entity may let a business associate handle ePHI "only if the covered entity obtains satisfactory assurances, in accordance with § 164.314(a)."

### 1c. Minimum necessary

The Privacy Rule minimum-necessary standard (45 CFR 164.502(b), 164.514(d)) is not quoted in this session. **UNVERIFIED in this pass.** The architectural consequence is standard practice: the LLM should receive only the fields a task needs, not the whole chart.

### 1d. The 2025 Security Rule NPRM: status

- **Proposed:** HHS OCR published the NPRM in the Federal Register on January 6, 2025 (90 FR 898). Source: https://www.hhs.gov/hipaa/for-professionals/security/hipaa-security-rule-nprm/index.html (HHS page; the body text did not render in this session, so the page was checked for existence and date only); Federal Register entry https://www.federalregister.gov/documents/2025/01/06/2024-30983/hipaa-security-rule-to-strengthen-the-cybersecurity-of-electronic-protected-health-information (not fetched directly; timed out).
- **What it would change** (per Clark Hill, 13 July 2026, https://www.clarkhill.com/news-events/news/hipaa-security-rule-update-delayed-until-2027/): eliminate the required/addressable distinction, require technology asset inventories and network mapping, mandate multi-factor authentication, expand encryption, require more prescriptive risk analysis and vulnerability testing, strengthen business associate oversight, and add detailed incident response and disaster recovery planning. The NPRM also proposed network segmentation (per Elisity, July 2026, a vendor source).
- **Status:** not final. The Fall 2026 Unified Agenda moved the rule (RIN 0945-AA22) to Long-Term Actions with a July 2027 target (Clark Hill, above; Medcurity, https://medcurity.com/hipaa-security-rule-delayed-2027/). Unified Agenda dates are planning estimates, not binding. Plan against the current rule, and treat the NPRM list as the likely direction.

## 2. What patient data the system holds

No primary HHS source was retrieved for this section. The structure below is standard practice from general knowledge, **UNVERIFIED against a primary source in this pass**.

- **Demographics:** name, DOB, sex, address, phone, email, preferred language, identifiers (MRN, SSN if collected).
- **Insurance coverage:** payer, plan, member ID, group number, subscriber relationship, effective and termination dates, copay and deductible. Coverage **changes over time**, so store it with effective dating (one row per coverage period), not as a single field on the patient. Eligibility answers are point-in-time.
- **Appointments:** scheduled, checked-in, completed, cancelled, no-show. Each carries a provider, a visit type, and a location.
- **Encounters:** the clinical visit, diagnoses (ICD-10-CM), procedures (CPT/HCPCS), and rendering provider.
- **Charges, claims, payments:** charges per encounter, claim submissions with status history, remittance postings, patient payments, adjustments, and balances.
- **Messages and calls:** portal messages, SMS, voicemail, and call recordings or transcripts. Transcripts are PHI when they name or describe a patient.

Architectural consequence: the store is append-heavy for events (charges, payments, messages) and effective-dated for coverage. Transcripts and recordings are a separate retention class.

## 3. Medical billing mechanics

- **CPT and HCPCS:** CPT is copyrighted by the American Medical Association. The AMA FAQ states that "any individual or entity using CPT content needs permission or a license." Source: https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs (fetched; the title and the license sentence are from the search snippet, the page body was not parsed). Two 2026 lawsuits challenge the AMA's CPT copyright and licensing: one filed by the Patient Rights Advocate (reported 13 August 2026, https://www.patientrightsadvocate.org/blog/patientrightsadvocateorg-sues-american-medical-association-to-make-medical-billing-codes-freely-available-to-the-public) and one by a patient group (reported 13 October 2026, https://telehealth.org/news/patient-advocacy-group-challenges-amas-cpt-copyright-in-federal-court/). Outcome **UNVERIFIED**. Architecture: the code set must be a licensed, versioned table, not hardcoded, and the license terms should be reviewed before any code list is redistributed to the model or to vendors. The advocacy-group fee figures ($82.50 annual plus $18.50 per user) are secondary and **UNVERIFIED** against the AMA price list.
- **ICD-10-CM:** a US government code set (CDC/NCHS), public domain. Diagnoses on claims come from here.
- **X12 837 and 835:** the 837 is the claim, the 835 is the electronic remittance advice (payment and adjustment reasons). CMS names ASC X12 Version 5010 as the adopted standard for these transactions, except retail pharmacy (CMS, https://www.cms.gov/priorities/key-initiatives/burden-reduction/administrative-simplification/hipaa/adopted-standards-operating-rules, search snippet, page body not parsed). Version 8020 and 5010 specifics are **UNVERIFIED in this pass**.
- **X12 270 and 271:** eligibility inquiry and response. These are the real-time or batch checks that answer "is this coverage active today." Same CMS source for the standard; transaction-level detail **UNVERIFIED**.
- **Clearinghouses:** a clearinghouse converts the practice's claim data into X12 and routes it to payers. The clearinghouse is a business associate. The practice does not send 837s directly to most payers.
- **Card payments:** processed by an outside payment processor. That processor is not a conduit for ePHI in the usual case (it receives card data and invoice data), and whether a BAA is needed depends on what patient data it sees. **UNVERIFIED in this pass.**

Architectural consequence: "local only" covers the models and the store. Claims, eligibility, remittances, card payments and phone carriers still traverse external networks. Each external party needs a documented assessment (see Section 4 on BAAs).

## 4. Business associate agreements and outside vendors

- **Rule:** a covered entity may let a business associate handle ePHI only with satisfactory assurances (45 CFR 164.308(b)(1), quoted above).
- **Conduit exception:** per Holland & Hart (14 April 2021, https://hhhealthlawblog.com/hipaa-business-associates-and-the-conduit-exception/), HHS's Omnibus Rule commentary says a conduit "transports information but does not access it other than on a random or infrequent basis." Its examples are the postal service and ISPs providing mere data transmission. The exception is narrow. **Phone carriers and ISPs that only transmit fit the conduit exception. A carrier that stores call recordings, voicemail, or transcripts does not.** Voicemail stored at a carrier or an IVR vendor is a business associate situation.
- **Cloud storage and backup:** HHS says "yes, provided the covered entity or business associate enters into a HIPAA-compliant business associate contract" for a cloud service that stores or processes ePHI (HHS FAQ, https://www.hhs.gov/hipaa/for-professionals/faq/may-a-hipaa-covered-entity-or-business-associate-use-cloud-service-to-store-or-process-ephi/index.html, search snippet). HHS cloud guidance (https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html) also says a CSP holding only encrypted ePHI with no key is still a business associate if it stores the data. Off-site or NAS-replicated backups held by a third party need a BAA. Backups kept only on hardware the practice owns are not a third-party case.
- **Clearinghouse:** business associate, BAA required.
- **Scheduling, reminder, and AI vendors:** BAA required if they touch PHI. A local model removes the vendor, not the need for a BAA if any vendor sees PHI (for example, a hosted SMS gateway).
- **Local models:** running a model on hardware the practice controls does not by itself create a business associate relationship with the model vendor, provided the vendor never receives PHI (for example, weights downloaded from a public hub). **UNVERIFIED as a settled HHS position.** If any model-updating, telemetry, or support channel sees patient text, treat that vendor as a business associate.

## 5. Open-source practice-management and EHR systems

- **OpenEMR:** GPL-3.0 (https://github.com/openemr/openemr). Version 8.0.0 released 11 February 2026 (OpenEMR wiki, https://www.open-emr.org/wiki/index.php/QA_and_Release_Process). ONC certification for version 7 was retired on 27 February 2026; version 8 is the certified line (OpenEMR wiki, https://www.open-emr.org/wiki/index.php/Release_Features). A CVE page (https://www.tenable.com/cve/CVE-2026-124488, dated 8 November 2026) states the fix is in "before 8.3.0", so 8.3.x is the line in use as of this date. Exact current patch level **UNVERIFIED** (the GitHub releases page did not render).
- **Coverage (general knowledge, not re-verified this pass):** scheduling, demographics, insurance, encounters, billing and claims (including 837 generation), patient portal, and the clinical record. It is the most complete free option.
- **Others:** other open-source practice systems exist but were not researched in this pass; **UNVERIFIED**.

Architectural consequence: a mature system of record exists. The AI layer should sit beside it, reading through its API or database views, not replacing its billing or audit functions.

## 6. LLM memory and patient data risks

- **OWASP Top 10 for LLM Applications** (https://genai.owasp.org/llm-top-10/): LLM02:2025 Sensitive Information Disclosure is listed. Prompt injection is the top risk in the list. A 2026 edition exists, reordering the 2025 list (HoneyHive summary, https://www.honeyhive.ai/learn/owasp-llm-top-10, search snippet only). Memory poisoning is named by secondary sources as a memory-based variant of injection (Superwise, https://superwise.ai/learn/owasp-top-10-for-llm-applications/); not verified against the OWASP list text.
- **Cross-patient leakage:** memory keyed by a patient must not be readable when the agent is working for another patient. This is an access-control question under 164.312(a)(1).
- **Patient-supplied text as an attack channel:** a patient's message or call transcript is untrusted input. Treat it as data, not instructions, before it enters memory.
- **Retention and deletion:** the HIPAA Security Rule requires documentation retention (164.316, **UNVERIFIED in this pass**). State medical record retention rules govern the record itself and are **UNVERIFIED** for any particular state.
- **Audit logging of memory reads:** 164.312(b) requires audit controls. 164.308(a)(1)(ii)(D) requires that the logs be reviewed. Each memory read that exposes PHI should be logged with the actor and the patient.
- **Human review of clinical content:** HHS and FDA guidance below. Administrative scheduling does not need clinical review; anything that suggests a diagnosis or triage does.
- **Regulatory guidance on AI:**
  - **Section 1557, 45 CFR 92.210:** bars discrimination through "patient care decision support tools," including AI, with a general prohibition effective 1 May 2025 (McDermott, https://www.mcdermottlaw.com/insights/section-1557-patient-care-decision-support-tools-anti-discrimination-compliance-12-things-to-consider/, search snippet). The text is not fetched in this pass. Applies to covered entities receiving federal financial assistance.
  - **ONC HTI-1 (2024)** added decision support transparency requirements for certified health IT. **HTI-5 (final, published 26 October 2026)** removes certain AI transparency requirements from HTI-1, including model card requirements for predictive decision support interventions (Holland & Knight, https://www.hklaw.com/en/insights/publications/2026/10/hti5-promotes-deregulatory-certification-actions).
  - **FDA Clinical Decision Support Software final guidance** was updated 6 January 2026 (https://www.fda.gov/media/191561/download, search snippet; body not parsed). It clarifies which CDS functions are FDA-regulated.
  - No HHS, ONC, or FDA document was found that specifically regulates an LLM handling scheduling or billing administration. **UNVERIFIED that none exists.**

## 7. Phone: reminders, automated calls, voicemail

- **TCPA baseline:** 47 U.S.C. 227(b)(1)(A)(iii) bars prerecorded or artificial-voice calls and autodialed calls to cell phones without prior express consent, except emergency calls (Rosenberger + Kawabata, 15 May 2026, https://www.rosenberger.law/blog/tcpa-healthcare-exemption/, quoting the statute at Cornell LII).
- **FCC 2015 order (FCC 15-72):** "provision of a phone number to a healthcare provider constitutes prior express consent for healthcare calls subject to HIPAA," limited to calls "closely related to the purpose for which the telephone number was originally provided" (FCC 15-72, https://docs.fcc.gov/public/attachments/FCC-15-72A1.pdf, as quoted by Rosenberger).
- **Free-to-patient exemption, 47 CFR 64.1200(a)(9)(iv)** (as quoted by Rosenberger from the eCFR 15 May 2026 snapshot; eCFR itself not fetched): permitted purposes include "appointment and exam confirmations and reminders, wellness checkups, hospital pre-registration instructions, pre-operative instructions, lab results, post-discharge follow-up intended to prevent readmission, prescription notifications, and home healthcare instructions." Conditions: no charge to the patient, **no more than one message per day and three per week** to each patient, no marketing or billing content, and STOP honored immediately. The exemption is for voice calls and texts to cell phones without consent.
- **HIPAA health care message, 47 CFR 64.1200(a)(2):** a HIPAA health care message can go on ordinary consent without written consent (Rosenberger).
- **Landline prerecorded calls, 47 CFR 64.1200(a)(3)(v):** no consent needed if at most one call per day and three per week per patient, with opt-out honored (Rosenberger).
- **Pending FCC action:** an FCC Report and Order and FNPRM (CG Docket 02-278) circulated 9 September 2026 for the 30 September 2026 open meeting would change revocation handling, including allowing an "exclusive means to revoke consent" and possibly requiring two-way texting for revocation. Source: https://docs.fcc.gov/public/attachments/DOC-424844A1.pdf (draft fact sheet, "remain under consideration and subject to change"). Adoption status **UNVERIFIED**; build the opt-out path so it can change.
- **Voicemail and what can be left:** HHS states "the HIPAA Privacy Rule permits health care providers to communicate with patients regarding their health care," and the FAQ addresses provider reminder messages at homes (https://www.hhs.gov/hipaa/for-professionals/faq/may-health-care-providers-leave-messages/index.html; only the first sentence was retrieved). Secondary sources say voicemail is allowed with minimal detail (Dial Raven, 30 July 2026; Modern Practice Solutions, 6 August 2025). The specific wording HHS gives on what detail to leave is **UNVERIFIED** from the primary page in this pass. Architecture default: a voicemail carries the practice name, a callback number, and an appointment reminder with no diagnosis, procedure, or test name.

## Architectural consequences

1. **Unique user IDs for every human and every agent identity** (164.312(a)(2)(i), (a)(1)). No shared logins; the AI layer has its own service identity.
2. **Access control on memory reads**, per patient, enforced below the model, not by prompt (164.312(a)(1); OWASP LLM02 cross-patient risk).
3. **Audit log of every PHI read, including memory reads**, with a scheduled review job (164.312(b); 164.308(a)(1)(ii)(D)).
4. **Encryption at rest and in transit, and automatic session logoff** (164.312(a)(2)(iii), (a)(2)(iv), (e)(2)(ii); all Addressable, so document the decision if not used).
5. **Integrity protections on ePHI** and tamper-evident audit trails (164.312(c)).
6. **Backup, disaster recovery, and an emergency mode that still schedules and takes calls** (164.308(a)(7)(ii)(A)-(C)). Test the restore.
7. **A risk analysis covering the LLM, the memory store, and the phone path** before go-live (164.308(a)(1)(ii)(A)).
8. **Business associate agreements** with the clearinghouse, any third-party backup or cloud store, any SMS or voice vendor that stores or sees content, and any payment processor that sees patient data. A carrier that only transmits may fall under the conduit exception (Holland & Hart).
9. **Licensed, versioned CPT table**; ICD-10-CM and X12 5010 generated, not hand-written (AMA FAQ; CMS).
10. **Coverage stored with effective dates**, because coverage changes over time and eligibility is point-in-time (270/271 checks).
11. **Retention policy per data class**: transcripts and recordings separate from the clinical record; deletion path for memory (state rules **UNVERIFIED**).
12. **Reminder engine enforces the FCC frequency cap, STOP handling, and free-to-patient limits in code**, not in a prompt (47 CFR 64.1200(a)(9)(iv)).
13. **Voicemail template with no clinical detail** (HHS FAQ; detail **UNVERIFIED**).
14. **Keep a human review gate for any clinical content** and log the Section 1557 and FDA CDS scope decision per feature (92.210; FDA CDS guidance).
15. **Build the consent and opt-out path to accept the pending FCC revocation changes** (FCC fact sheet, 9 Sep 2026).

## Sources

- HHS, HIPAA Security Rule NPRM page: https://www.hhs.gov/hipaa/for-professionals/security/hipaa-security-rule-nprm/index.html
- HHS, Summary of the HIPAA Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html (fetched, partial)
- 45 CFR 164.312 (Cornell LII): https://www.law.cornell.edu/cfr/text/45/164.312
- 45 CFR 164.308 (Cornell LII): https://www.law.cornell.edu/cfr/text/45/164.308
- eCFR 45 CFR 164.312 (not fetched; bot-blocked): https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312
- Federal Register, NPRM (timed out): https://www.federalregister.gov/documents/2025/01/06/2024-30983/hipaa-security-rule-to-strengthen-the-cybersecurity-of-electronic-protected-health-information
- Clark Hill, HIPAA Security Rule delay, 13 Jul 2026: https://www.clarkhill.com/news-events/news/hipaa-security-rule-update-delayed-until-2027/
- Medcurity, delay to July 2027: https://medcurity.com/hipaa-security-rule-delayed-2027/
- HHS Business Associates FAQ: https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html (search snippet only)
- Holland & Hart, conduit exception, 14 Apr 2021: https://hhhealthlawblog.com/hipaa-business-associates-and-the-conduit-exception/
- HHS, cloud service FAQ: https://www.hhs.gov/hipaa/for-professionals/faq/may-a-hipaa-covered-entity-or-business-associate-use-cloud-service-to-store-or-process-ephi/index.html (search snippet)
- HHS, Guidance on HIPAA and Cloud Computing: https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html (search snippet)
- AMA, CPT licensing FAQ: https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs
- Patient Rights Advocate, AMA suit (13 Aug 2026): https://www.patientrightsadvocate.org/blog/patientrightsadvocateorg-sues-american-medical-association-to-make-medical-billing-codes-freely-available-to-the-public
- Telehealth.org, patient group suit (13 Oct 2026): https://telehealth.org/news/patient-advocacy-group-challenges-amas-cpt-copyright-in-federal-court/
- CMS, Adopted Standards and Operating Rules (16 Mar 2026): https://www.cms.gov/priorities/key-initiatives/burden-reduction/administrative-simplification/hipaa/adopted-standards-operating-rules
- OpenEMR GitHub: https://github.com/openemr/openemr
- OpenEMR wiki, QA and Release Process: https://www.open-emr.org/wiki/index.php/QA_and_Release_Process
- OpenEMR wiki, Release Features: https://www.open-emr.org/wiki/index.php/Release_Features
- Tenable, CVE-2026-124488: https://www.tenable.com/cve/CVE-2026-124488
- OWASP Top 10 for LLM Applications: https://genai.owasp.org/llm-top-10/
- HoneyHive, OWASP LLM summary: https://www.honeyhive.ai/learn/owasp-llm-top-10 (secondary)
- McDermott, Section 1557 decision support tools: https://www.mcdermottlaw.com/insights/section-1557-patient-care-decision-support-tools-anti-discrimination-compliance-12-things-to-consider/ (secondary)
- Holland & Knight, HTI-5 (28 Oct 2026): https://www.hklaw.com/en/insights/publications/2026/10/hti5-promotes-deregulatory-certification-actions
- FDA, Clinical Decision Support Software final guidance (6 Jan 2026): https://www.fda.gov/media/191561/download
- Rosenberger + Kawabata, TCPA healthcare exemption (15 May 2026): https://www.rosenberger.law/blog/tcpa-healthcare-exemption/ (secondary; quotes 47 CFR 64.1200 and FCC 15-72)
- FCC 15-72, 2015 TCPA Declaratory Ruling: https://docs.fcc.gov/public/attachments/FCC-15-72A1.pdf (cited via Rosenberger; not fetched directly)
- FCC fact sheet and draft R&O, CG Docket 02-278 (9 Sep 2026): https://docs.fcc.gov/public/attachments/DOC-424844A1.pdf
- HHS, May providers leave messages for patients (FAQ): https://www.hhs.gov/hipaa/for-professionals/faq/may-health-care-providers-leave-messages/index.html (first sentence only)
- Dial Raven, HIPAA voicemail (30 Jul 2026): https://dialraven.com/blog/hipaa-compliant-voicemail (secondary)

## Could not verify

- eCFR text for 164.312 and 64.1200 (bot-blocked); quoted via LII and Rosenberger.
- Full HHS voicemail and minimum-necessary wording.
- Federal Register NPRM body text (timed out); NPRM contents taken from Clark Hill.
- Current OpenEMR patch release (only the 8.3.0 fix line is evidenced).
- X12 version 8020 and transaction-level specifics; card-processor BAA position.
- Outcome of the 2026 CPT copyright suits; advocacy-group fee numbers.
- Whether any HHS, ONC, or FDA document specifically addresses LLMs in administrative scheduling or billing.
- Section 2 (data structure) and Section 5 coverage details rest on general knowledge, not a primary source.
