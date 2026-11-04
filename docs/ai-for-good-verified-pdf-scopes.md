# Verified PDF scope corrections

Checked 4 November 2026 against the three supplied official PDFs. Corpus version
is now **2026-11-04.4**, with **13 records**: 10 general and three UAEU-only.
Original source PDFs are not redistributed in the repository or KB packages.

| Reference | Exact locator checked | Corpus interpretation |
| --- | --- | --- |
| [TDRA National Policy for Digital Accessibility](https://dgov.tdra.gov.ae/-/media/dgov/pdfs/publications/national-digital-accessibility-policy-en.pdf) | Article 3, PDF/printed page 7; Annex 1 section 1, page 13; March 2024 cover | Article 3 lists federal bodies and specified regulated/government-connected parties, plus best-efforts consideration for local, semi-government and private entities. The annex's public-service-site WCAG 2.1 AA provision is read within this policy context. A private university's coverage is not established merely by location/type. |
| [UAE AI Ethics: Principles and Guidelines](https://ai.gov.ae/wp-content/uploads/2023/05/MOCAI-AI-Ethics-EN.pdf) | Section 1.1, PDF p.3/printed p.5; section 1.2, PDF p.4/printed p.6; licensing section 1.5, PDF p.5. Cover: December 2022 | Non-binding guidance targeting AI that makes or informs significant decisions, including critical decisions. Ordinary rehearsal uses it as voluntary design guidance unless the real use meets that scope. It is distinct from the beta self-assessment tool. |
| [UAEU student GenAI policy](https://www.uaeu.ac.ae/en/about/pdfs/policies-2025/generative-ai-policy.pdf) | Scope and surrounding overview, PDF p.2; effective 11 August 2025 and next review 1 September 2027 | UAEU students and covered student work, including academic-credit and on/off-campus university work. Do not turn it into a general policy for all UAE universities or generic staff rehearsal. |

TDRA pages 7/13 and UAEU page 2 were checked using local PDF extraction/rendering
and visual inspection. AI ethics sections were read in the official web-extracted
PDF; direct local download returned HTTP 403, so no local-copy or whole-document
visual verification is claimed for it. The two local input hashes were TDRA
`6f6703fbea05d4c0deb67c6df17c77f292a353f65931fe65833424ab57cd77da`
and UAEU `a47a8310b321122b044a9ec90ab924972d94103b9306e0692941ef9a957c20d8`.

The verified policy/guidance pages **do not verify current statutory PDPL text,
cross-border transfer conditions or applicability to an actual institution**.
Those existing limitations remain explicit in the corpus. No legal compliance,
WCAG conformance, endorsement or certification is inferred from a citation.

## Changes and verification

- Added separate TDRA-policy and AI-ethics-principles records with the relevant
  scope, locators, issue dates and reuse conditions; retained the separate toolkit.
- Tightened UAEU's student/staff boundary and kept institution selection explicit.
- Kept WCAG/digital-accessibility terms in topic retrieval. An explicit WCAG
  review now finds the TDRA record and begins with its Article 3 scope check.
- Regenerated original-summary KB inputs: general 10 documents/29 chunks; UAEU
  13 documents/38 chunks. Both deterministic checks pass. No embeddings or hosted
  import were performed, and no raw PDF was included in those packages.
- Added scope regressions covering API output, review wording and package content.

The two approved live evaluations and their historical plans remain unchanged.
The [new corpus-specific dry plan](evidence/ai-for-good-coordination-plan-v3-corpus4.json)
uses corpus .4 without making requests; it is not a third live evaluation.
The source-fit and institutional-review work in the
[remaining-requirements list](ai-for-good-source-review-and-next-steps.md) remains
open. These narrower source corrections do not prove the deployment is in scope.

Final offline verification passed 90 existing backend checks, 87 policy-related unit tests (including scope and export regressions), the standalone scenario verifier, 97 frontend tests, frontend/API builds and an extracted-wheel scope-first review check. Both scoped KB regeneration checks passed. No model/provider calls or uploads occurred in this update.
