# Independent implementation and source review

Review baseline: `eb52b6c`, 4 November 2026. A separate reviewer reproduced the
issues below without making code changes or calling external model providers.
Owners fixed them, and the reviewer then reran the original reproductions.

## Confirmed findings and repairs

| Finding | Resulting behavior | Focused evidence |
| --- | --- | --- |
| A decision from an old view could be logged under a newer stage | Advance and decision requests require the viewed `expected_stage`; stale writes return 409 under the store lock before mutation | Two stage-1 advances produce one stage-2 response and one 409; a stale decision adds no event |
| A human decision could have no evidence reference | At least one released fact visible to the role is required; the UI explains and enforces this | Empty or missing fact references return 422; a fresh referenced decision succeeds |
| Injected topic anchors were described as matches to submitted wording | Audit separates direct input matches, alias-derived matches and topic anchors; topic-only selection is identified as such | Unrelated wording plus a selected privacy topic has no input matches and explicitly records anchor terms |
| Model-selected citations could retain the deterministic source's audit terms | Model-assisted audits are rebuilt from the sources actually selected | An offline double choosing a non-first candidate records only that candidate's term groups and citation IDs |
| UNESCO adoption and publication dates were conflated | Recommendation publication is 2022; adoption in 2021 is recorded separately | Official overview metadata checked; full-text section verification remains limited |

The first four reproductions passed on independent recheck. This verifies those
specific software behaviors, not general advice quality or security certification.

## What the scenarios actually demonstrate

| Area | Expected local behavior | What is established | What is not established |
| --- | --- | --- | --- |
| Progressive disclosure | Future facts and stage titles are absent from initial views | Three fixed stages are released in order with stale-write protection | Real incident feeds or action-dependent branching |
| Uneven information | Teacher, privacy and accessibility views receive different released facts | Role projections and filtered human activity views | Authenticated institutional mandates or autonomous institutional agents |
| Source attribution | Considerations cite records from the selected collection with honest term provenance | Scope filtering, selected-source IDs and separate input/alias/anchor terms | The relevance or correctness of policy advice in every case |
| Human supervision | A person records a stage-specific decision citing visible evidence | Nonempty fact references and stage checks | That a human decision was appropriate or applied in a real institution |
| Policy gaps | A discussion can expose missing deployment facts and ownership questions | Synthetic uncertainties and global comparison references are available | Validated gaps in UAE law, university policy or technical standards |

The official brief invites one or more agent roles; autonomous institutional
coordination is not an unconditional requirement for every submission. YapLab
must nevertheless avoid representing selectable views as independent agents.
The current policy model mode selects retrieved references; it does not conduct
an autonomous institutional assessment or generate a validated gap analysis.

## Source and operating limits

Accessible UAEU official PDFs supported the checked paraphrases and institutional
scope. The UAE legislation endpoints returned HTTP 403; indexed official
provisions corroborate only parts of the cited laws. UNESCO official overviews
were checked, while complete linked publication text was not independently
verified in this pass. The corpus exposes those limits with each reference.

Exercises have an access TTL and bounded process-local capacity. Expired entries
are removed lazily on a subsequent exercise operation or process shutdown; there
is no background erasure guarantee at the exact expiry time. Use synthetic data.
Roles are selectable views and random exercise IDs are capabilities, not account
authentication. Request and model budgets reset with the process and do not
replace provider account controls.

## Remaining validation and access dependencies

An educator and an institutional policy reviewer should assess the scenarios and
their actual applicability, compare expected responses with a labelled rubric,
and assess whether the global examples address the same problem. Any live-model
evaluation needs approved provider access and a bounded budget. Neither such
evaluation nor a real user study has been performed.

Final submission destination, hosted KB schema/access and acceptance of the
summary corpus still require organiser instructions. No hosted import, model
fine-tuning, legal compliance, validated policy gap or educational benefit is
claimed. The final report also awaits supported DOCX rendering and pagination.
