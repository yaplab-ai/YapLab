# AI for Good: policy source notes

The [AI for Good Lab Hackathon UAE brief](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485) asks teams to map a use-case knowledge base to country policies and global best practices. The accompanying [seed corpus](../apps/api/frontrow/policy/corpus.json) supports English-language guidance for general university teachers and teaching assistants. It contains curated source metadata and short original paraphrases, not the complete underlying documents. Sources were reviewed on **2026-11-04**.

## How to interpret the sources

| ID | Authority and locator | Relevance and applicability |
| --- | --- | --- |
| `uae-personal-data-protection` | [UAE Legislation: Federal Decree by Law No. 45 of 2021](https://uaelegislation.gov.ae/en/legislations/1972), particularly Articles 2–5, 13–19 and 22–23 | Federal personal-data law. Check scope, exclusions, processing basis, data-subject rights and transfer conditions for the actual institution and use. |
| `uae-persons-with-disabilities-education` | [UAE Legislation: Federal Law No. 29 of 2006](https://uaelegislation.gov.ae/en/legislations/1172), Articles 12–13 | Education rights and responsibilities relevant beyond schools; Article 13 identifies the higher-education ministry. Check amendments and current implementing measures. |
| `uae-ai-ethics-self-assessment` | [UAE AI Office: AI Ethics Self-Assessment Tool](https://ai.gov.ae/aiethics-self-assessment/), purpose and contents | Voluntary beta self-assessment for AI developers and operators. It is neither education-specific nor a certification. |
| `uae-inclusive-education-schools` | [UAE Ministry of Education: Inclusive Education](https://moe.gov.ae/en/Pages/DeterminationInclusiveEducation.aspx), 2020 policy and implementation overview | A useful inclusion design example, but the cited policy concerns schools following the Ministry curriculum; do not claim it binds universities. |
| `unesco-generative-ai-education` | [UNESCO: Guidance for Generative AI in Education and Research](https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research), sections 2–5 | Global human-centred guidance, including privacy, pedagogical design and critical review of generated outputs. |
| `unesco-ai-ethics-recommendation` | [UNESCO: Recommendation on the Ethics of Artificial Intelligence](https://www.unesco.org/en/articles/recommendation-ethics-artificial-intelligence), principles and policy action areas | International recommendation on human rights, fairness, transparency and oversight, including education. |
| `england-generative-ai-education` | [England Department for Education: Generative AI in Education](https://www.gov.uk/government/publications/generative-artificial-intelligence-in-education/generative-artificial-intelligence-ai-in-education), opportunities, responsible use and assessment sections | Cross-country example for educator review and privacy. It is aimed principally at schools and colleges and does not establish UAE legal requirements. |

## Use and maintenance

Citations should identify the source, jurisdiction, locator and caveat, and distinguish enforceable law from voluntary guidance and international examples. The `requirements` field records relevant considerations in original language; it does not claim that every item is a binding obligation. Avoid asserting that a generated lesson or product is legally compliant or accessible merely because it matches a corpus entry.

Before consequential use, check the latest official Arabic legislation, amendments, implementing regulations, emirate and free-zone rules, and the university's own privacy, accessibility, assessment and AI policies. The UAE legislation pages provide English translations; use the authoritative text for legal interpretation. The source list is deliberately selective and does not cover every applicable law, university policy, discipline or learner need. Refresh the version and retrieval date after a substantive source review.


## University-specific reference collection

The `uaeu` collection adds three public institutional examples. General search
and review exclude them. Selecting this collection does not establish that the
user is affiliated with UAEU or that a policy applies to a particular deployment.

| Record | Official source and locator | Boundary |
| --- | --- | --- |
| `uaeu-student-generative-ai` | [Student GenAI policy](https://www.uaeu.ac.ae/en/about/pdfs/policies-2025/generative-ai-policy.pdf), pp. 2–4; effective 11 August 2025, review 1 September 2027 | UAEU student academic-credit work; not a universal university rule. Its detector provision must not be treated as proof of detector reliability. |
| `uaeu-institutional-data-governance` | [Data governance policy](https://www.uaeu.ac.ae/en/about/pdfs/policies-2025/data-governance-policy.pdf), pp. 2–6 | UAEU institutional data; research-only data is excluded. |
| `uaeu-students-of-determination-services` | [Support services](https://www.uaeu.ac.ae/en/student-services/special-needs/services.shtml), Services section | Institutional service guidance, not legislation. |

The [approved-policies index](https://www.uaeu.ac.ae/en/about/bylaws-policies-procedures.shtml)
links the policy PDFs. UAEU’s [copyright notice](https://www.uaeu.ac.ae/en/website/copyright.shtml)
requires permission for reproduction. The corpus and local export contain links,
metadata and original paraphrases; they do not redistribute those PDFs. A wider
full-text corpus needs a rights review first.

The current legislation pages returned HTTP 403 in the second review. Their
official indexed provisions were corroborated, but full current texts and
amendments remain a verification task. In particular, the federal privacy law’s
Article 2 exclusions prevent assuming that every university falls under that
regime. No legal applicability determination is made here.

## National strategy context

The [UAE AI Office strategy page](https://ai.gov.ae/strategy/) supplies a distinct
strategy record (`uae-national-ai-strategy-2031`). Objectives on talent, enabling
infrastructure and governance help frame project design. This is strategic
context rather than legal authority, institutional approval or evidence that
YapLab achieves national outcomes. Historical projections are not reused.
