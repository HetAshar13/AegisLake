# Card reconciliation contract

The demo covers synthetic single-capture card payments keyed by authorization ID. Source records come from authorizations, gross settlements and the ledger. The expected ledger leg is one DEBIT for the gross settlement amount in its currency. Fees are reported separately. Source money uses integer minor units. Comparisons require both legs and matching currencies.

The demo's UTC clock is 12:00 on 7 November 2026. A missing settlement is pending before its 60-minute deadline and overdue at the deadline. Standalone settlements and ledger postings remain visible. Preserve all break reasons when several checks fail. Match-rate reporting includes assessed cases and lists pending cases separately.

Merchant and customer IDs resolve through the fixture registry. An unknown dimension ID is visible in the output. The input includes a malformed amount and an identical ledger redelivery.

An event ID identifies one source payload. A correction supplies a new event ID and a higher source-specific event version for the same case. Repeated identical delivery has one business effect. Conflicting payloads for the same event identity or case version must be surfaced before joining. As-of assessments use source timestamps.

The expected-results file defines the independently reviewed outcomes. The project evidence should report only actual test runs, measured throughput, demonstrated deployments and exercised features. Retire the hard-coded metrics and claims of double-entry accounting, automated repair, regulatory signoff and guaranteed model accuracy from the demo path.
