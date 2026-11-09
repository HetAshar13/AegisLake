# AegisLake: 360° Career Packaging, CV Blueprints & Showcase Playbook

> **Author:** Het Hargovind Ashar  
> *MSc Computer Science & Engineering — Politecnico di Milano*  
> **Target Institutions:** Revolut (London/Milan), ION Group (Milan), Databricks (Amsterdam/Munich), Amazon (Milan/Dublin), Bending Spoons (Milan)

---

## 1. Tailored CV Bullet Points (Google XYZ Format)

Use the corresponding bullet set on your resume depending on the job posting you are targeting.

### Set A: Data Engineering & Lakehouse Platform Roles
*(Targeting Revolut Data Platform, ION Group FinTech, Databricks, Amazon)*

* **AegisLake — Self-Healing Financial Lakehouse & Reconciliation Platform** | *Lead Architect*
  * "Architected an end-to-end financial data lakehouse ingesting 5,000+ payment events/sec across Card, SEPA, and FX rails using PySpark Structured Streaming with 10-minute watermarking and Delta Lake Change Data Feed (CDF)."
  * "Engineered a high-performance three-way reconciliation engine in dbt Core and DuckDB, modeling Kimball star schemas with 100% test coverage across 40 custom financial invariants and enforcing double-entry zero-balance constraints."
  * "Automated multi-environment cloud infrastructure using Terraform (AWS S3, customer-managed KMS encryption, BucketOwnerEnforced policies) and Databricks Asset Bundles (DAB) with dedicated Spot Job Clusters, reducing infrastructure provisioning time by 90%."
  * "Eliminated IEEE 754 floating-point rounding errors across multi-currency ledgers by implementing an ISO-4217 integer minor-unit engine supporting 0-decimal (JPY), 2-decimal (EUR/USD), and 3-decimal (BHD) currencies."

---

### Set B: Applied AI & Autonomous Agent Systems Roles
*(Targeting Revolut Applied AI, Bending Spoons, AI Platform Teams)*

* **AegisLake — Autonomous Financial Incident Commander** | *Lead AI Systems Architect*
  * "Engineered an autonomous multi-agent incident commander in LangGraph 1.2+, orchestrating a 4-agent cyclic state machine that diagnoses financial ledger breaks and generates validated dbt/SQL remediation patches in < 0.70 seconds."
  * "Eliminated LLM hallucinations in data lineage by compiling SQL abstract syntax trees (AST) via SQLglot, mathematically tracing column-level provenance in O(V+E) time (0.02s) with zero token burn."
  * "Integrated Gemini 3.5 Flash-lite with an in-memory DuckDB shadow validation sandbox, automatically self-healing syntax errors before surfacing patches to auditors."
  * "Implemented strict Sarbanes-Oxley (SOX-404) and EU DORA regulatory compliance by designing a Human-in-the-Loop (HITL) interrupt gate with cryptographic audit signoffs, preventing unauthorized automated ledger updates."

---

### Set C: Analytics Engineering & FinTech Business Intelligence Roles
*(Targeting Satispay, Scalapay, Booking.com, FinTech Analytics)*

* **AegisLake — Multi-Rail Payment Intelligence & Semantic Layer** | *Lead Analytics Engineer*
  * "Constructed an executive financial intelligence platform modeling multi-rail card authorizations, clearinghouse settlements, and quarantine breaks across EUR, USD, GBP, and JPY currencies."
  * "Developed an interactive Power BI semantic model featuring 10 production DAX measures (Gross Capital at Risk, Reconciliation Match Rate %, Authorization Volume, Break Aging) with zero-tolerance reconciliation parity against DuckDB ground truth."
  * "Built an interactive Streamlit Mission Control dashboard enabling financial auditors to simulate real-time Poisson payment streams, inject live chaos faults, and review autonomous incident diagnoses with one click."

---

## 2. 120-Second Video Demonstration Storyboard & Script

Record this 2-minute walkthrough using **Loom** or **OBS** (desktop view on `http://localhost:8501`, your webcam in the bottom-right corner). Pin this video to your LinkedIn profile and link it in your GitHub README!

### [00:00 - 00:20] Hook & Business Context
* **Screen:** Tab 1 of Streamlit Mission Control showing the live multi-rail transaction stream and the Poisson throughput chart.
* **Script:**
  > *"Hi everyone, I'm Het Ashar, MSc Computer Science student at Politecnico di Milano. In modern FinTechs like Revolut or payment processors like Stripe, millions of card authorizations, SEPA transfers, and clearinghouse settlements arrive out of order across different currencies every second. A single discrepancy between what was authorized and what settled can lead to regulatory fines and balance sheet contamination. I built **AegisLake**, an enterprise self-healing financial lakehouse and autonomous incident control plane."*

### [00:20 - 00:45] The Lakehouse & Chaos Injection
* **Screen:** Click the red button `🚨 Inject Amount Mismatch`, then click `⚠️ Inject Currency Drift`. Watch the toast appear and the live feed update.
* **Script:**
  > *"Under the hood, AegisLake ingests high-velocity streaming events with Poisson inter-arrival times into PySpark and Delta Lake. It uses 10-minute event-time watermarking to eliminate duplicate transactions and extracts Change Data Feed (CDF) for real-time tracking. Watch as I inject an on-demand chaos fault—an amount mismatch of €49.00 on a card scheme. The PySpark dual-routing engine instantly catches the contract breach and routes it to an isolated Dead-Letter Quarantine table to protect our downstream financial reports."*

### [00:45 - 01:15] The Star Demo: Autonomous Copilot & SQLglot AST Lineage
* **Screen:** Switch to **Tab 3: Autonomous Incident Commander (HITL)**. Select `AUTH_004`. Click `🚀 Run Autonomous Incident Commander`.
* **Script:**
  > *"Now, how do we fix this break? Rather than waiting hours for an on-call data engineer, our LangGraph 1.2+ multi-agent Incident Commander takes over. Look at what happens in under 0.7 seconds: First, it compiles the dbt SQL DAG using SQLglot compiler ASTs to mathematically trace the exact column lineage—from Bronze Kafka events all the way to fact_reconciliation_breaks—in 0.02 seconds with zero LLM hallucination. Then, it queries the quarantine payload and uses an LLM in a shadow sandbox to draft a precision SQL remediation patch."*

### [01:15 - 01:40] Bank Compliance (HITL) & Power BI
* **Screen:** Click `✅ Approve Patch & Apply (Lead Auditor)`. Watch the green **Official Regulatory Audit Certificate** seal appear. Then quickly show the Power BI Dashboard.
* **Script:**
  > *"Because banking regulations like SOX-404 and EU DORA prohibit autonomous AI from altering financial books of record without human attribution, our agent pauses at a Human-in-the-Loop gate. Once I inspect the proposed patch and click Approve, the thread resumes, generates an immutable cryptographic audit certificate, and publishes clean metrics to our Power BI semantic model with 10 production DAX measures."*

### [01:40 - 02:00] Cloud Architecture & Wrap-Up
* **Screen:** Briefly show the GitHub repository and terminal with 96 passed tests.
* **Script:**
  > *"The entire platform is backed by modular AWS Terraform IaC, Databricks Asset Bundles (DAB), and a 96-test automated verification suite. You can check out the open-source code and system design playbook on my GitHub. Thank you!"*

---

## 3. High-Impact LinkedIn Case Study Post Draft

Copy, paste, and post this on LinkedIn with a 30-second clip or screenshot of the Streamlit Mission Control UI:

```markdown
🚀 Excited to unveil AegisLake: A Self-Healing Financial Data Lakehouse & Autonomous Reconciliation Control Plane.

In multi-rail FinTech architectures (handling Card Schemes, SEPA Instant, and FX settlement), matching internal authorizations against clearinghouse settlement legs is one of the hardest distributed systems problems:
❌ Out-of-order event streams cause silent duplicate postings.
❌ Floating-point arithmetic truncates fractional pennies across currency corridors.
❌ Diagnosing multi-table schema breaks takes hours of manual SQL lineage tracing.

To solve this from first principles, I engineered AegisLake:

🏗️ Distributed Lakehouse Architecture:
• Real-Time Event Streaming: Parameterized Poisson ingestion (5,000+ EPS) via Redpanda / Kafka.
• PySpark Delta Lake Medallion: 10-minute watermarking deduplication with Delta Change Data Feed (CDF) for low-latency incremental updates.
• Zero-Truncation Currency Engine: Full integer minor-unit arithmetic with ISO-4217 dynamic scaling for 0-decimal (JPY), 2-decimal (EUR/USD), and 3-decimal (BHD) currencies.
• Kimball Dimensional Modeling: dbt Core + DuckDB star schema enforcing double-entry zero-balance invariants.

🤖 Autonomous Incident Commander (LangGraph 1.2+):
• Deterministic AST Lineage: Employs SQLglot compiler ASTs to traverse column provenance in O(V+E) time (0.02s)—eliminating LLM token burn and hallucination.
• Shadow-Tested Remediation: Synthesizes compensating journal entries tested in an isolated DuckDB sandbox before presentation.
• SOX-404 & EU DORA Compliance: Interactive Human-in-the-Loop (HITL) interrupt gate with cryptographic audit signoffs.

☁️ Cloud IaC & Enterprise Orchestration:
• AWS Terraform: S3 Medallion storage with customer-managed KMS key rotation, BucketOwnerEnforced ownership, and least-privilege IAM roles.
• Databricks Asset Bundles (DAB): Automated 4-stage Lakeflow DAG running on dedicated Spot Job Clusters.
• Verification: 96 automated tests verified 100% GREEN (Pytest + dbt invariant assertions).

Special thanks to the open-source data engineering and AI community! 

Check out the full repository and 20-question system design playbook here:
👉 GitHub: https://github.com/HetAshar13/AegisLake

#DataEngineering #FinTech #PySpark #DeltaLake #Databricks #LangGraph #dbt #AWS #SystemDesign #DistributedSystems #PolitecnicoDiMilano
```
