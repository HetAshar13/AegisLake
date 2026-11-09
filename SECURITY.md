# Security Policy & Cryptographic Governance

## 1. Security Overview & Compliance

**AegisLake** is architected to satisfy the stringent data integrity and confidentiality requirements of modern financial institutions governed by:
- **Sarbanes-Oxley Act (SOX-404):** Section 404 internal controls over financial reporting, requiring strict segregation of duties, immutable audit logging, and prohibiting autonomous unauthorized modification of ledgers.
- **EU Digital Operational Resilience Act (EU DORA):** High-availability operational resilience, continuous fault tolerance testing (Chaos Engine), and rigorous ICT incident reporting.
- **PCI-DSS & ISO 27001:** Zero-trust cloud storage, end-to-end encryption at rest and in transit, and least-privilege identity access management.

---

## 2. Cryptographic Storage & Encryption-at-Rest

All transaction payloads, Medallion storage partitions, and quarantine tables in AWS S3 are protected using **Customer-Managed AWS KMS Keys (SSE-KMS)**:
- **Key Rotation:** Automatic 365-day rotation is strictly enforced in Terraform (`enable_key_rotation = true`).
- **Access Control:** S3 buckets enforce `BucketOwnerEnforced` to disable legacy ACLs and prevent permission hijacking.
- **Zero Public Access:** All four S3 public access block flags are permanently active.

---

## 3. Human-in-the-Loop (HITL) Regulatory Safety

Autonomous AI agents in AegisLake operate under a strict **Zero-Hallucination, Zero-Autonomous-Write** governance boundary:
1. **Deterministic Lineage:** Provenance is traversed deterministically via SQLglot Abstract Syntax Trees (AST); LLMs are never permitted to guess data relationships.
2. **Shadow Sandbox:** Remediation SQL patches are executed in an isolated, read-only DuckDB sandbox prior to presentation.
3. **HITL Interrupt:** Ledger updates require explicit, attributed human review and sign-off via LangGraph `interrupt()` primitives before any compensating entry is finalized.

---

## 4. Reporting a Security Vulnerability

If you discover a security vulnerability or credential leak within AegisLake, please disclose it responsibly:
- **Lead Security Architect:** Het Hargovind Ashar
- **Email:** `hetashar13@gmail.com`
- **Response SLA:** Initial acknowledgment within 24 hours, followed by a remediation patch within 72 hours.
- Please do **not** open a public GitHub issue for security disclosures.
