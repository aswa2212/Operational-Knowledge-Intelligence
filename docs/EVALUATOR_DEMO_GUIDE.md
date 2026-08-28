# OKI Mini-Project: Master Evaluator Presentation & Demo Guide

---

## 1. Core Clarification: Are Slack, Notion, and GitHub the "Agent"?

**Direct Answer:** No. Slack, Notion, and GitHub are **external systems** that serve two distinct roles in the OKI architecture:

1. **As Data Sources (Inputs):** They are the messy places where company operational knowledge lives (e.g. GitHub issues, Notion wikis/policies, Slack engineering discussions). OKI connects to them via APIs and syncs their raw text into the `documents` table.
2. **As Execution Environments / Tools (Outputs):** When OKI needs to perform an action in the real world, it invokes tool adapters (e.g. `GitHubCommentTool` posts a comment on an issue, `GitHubLabelTool` adds a tag, `SlackNotifyTool` alerts an on-call engineer).

**What is the "Agent"?**
The **Agent** is the core **OKI Engine** (the orchestrator running on your backend). It reads the versioned, mathematically resolved rules from `skills_artifacts/`, ingests cases, executes deterministic/fuzzy reasoning, checks the deterministic **Risk Matrix Gate**, and autonomously decides whether to call external tools or escalate to a human manager.

---

## 2. Master Demo Structure (~10–12 Minutes Total)

This structure provides **maximum depth on the primary flow** while proving **broad generalization across all 3 business domains** without repetitive screen-hopping.

| Section | Focus Area | Process / Feature | Duration | Key Takeaway for Evaluator |
| :--- | :--- | :--- | :---: | :--- |
| **Intro & Pitch** | The Problem | RAG Failure vs. Rule Resolution | 1.5 min | Why raw document retrieval fails when policies conflict. |
| **Part A** | Full 9-Step Flow | `refund_handling` (Low Risk) | 5 min | The entire autonomous pipeline from sync to execution. |
| **Part B** | Bounded Autonomy | `refund_handling` (High Risk) | 2.5 min | The Human-in-the-Loop gate for high-value operations. |
| **Part C** | Generalization | `incident_triage` & `pricing_exceptions` | 2 min | Proves the architecture is domain-agnostic. |
| **Part D** | Empirical Proof | Evaluation Ablation & Database | 1.5 min | Quantitative proof that weighted resolution beats naive baselines. |

---

## 3. Step-by-Step Live Evaluator Presentation Script

### 🎙️ Introduction (1.5 min)
- **Open:** [http://localhost:5173](http://localhost:5173)
- **Say:** *"Modern AI agents fail in real enterprises not from lack of intelligence, but because operational rules are fragmented and contradictory across systems like GitHub, Notion, and Slack. Standard RAG injects these contradictions into prompts, causing hallucinated actions. OKI extracts discrete operational rules, mathematically resolves conflicts into versioned skills, and executes decisions behind a strict Risk Matrix Gate."*

---

### 🔹 Part A: The Full 9-Step Pipeline Walkthrough (~5 min)

*Use Process:* **`refund_handling`** | *Fixture:* **`fx-004`** (Small order, within window)

1. **Step 1: Sync Sources (`/sources`)**
   - Click on **Sources** in the left sidebar.
   - Point to the connected sources: **GitHub Issues** (`aswa2212/OKI`), **Notion Workspace**, and **Synthetic Enterprise Data**.
   - Click **Sync** on the GitHub source to demonstrate live API ingestion.
2. **Step 2: Ingested Documents (`/documents`)**
   - Click on **Documents** in the sidebar.
   - Show the evaluator the normalized documents with author seniority weights ($0.35$ for support chats, $0.95$ for executive policy documents).
3. **Step 3 & 4: Conflict Resolution (`/conflicts`)**
   - Click on **Conflicts** in the sidebar.
   - Show how OKI groups contradictory candidate rules and applies its 4-factor scoring formula:
     $$\text{Score} = 0.35 \times \text{Recency} + 0.40 \times \text{Authority} + 0.15 \times \text{Corroboration} + 0.10 \times \text{Override}$$
   - Highlight: Clear winners ($\text{Score} \ge 0.70, \text{Margin} \ge 0.05$) become active rules, while genuine ambiguities are routed to Knowledge Review.
4. **Step 5: Compiled Skills Browser (`/skills`)**
   - Click on **Skills Browser** and select `refund_handling`.
   - Show the active compiled YAML artifact (`v023.yaml`).
   - *Say:* *"This versioned YAML artifact is the agent's executable ground truth — clean, deterministic, and contradiction-free."*
5. **Step 6 & 7: Case Intake & Autonomous Decision (`/cases`)**
   - Click on **Case Runner** in the sidebar.
   - Select Process: `refund_handling`.
   - Enter Low-Risk Inputs:
     - **Days Since Purchase:** `5`
     - **Order Value ($):** `35`
     - **Customer Tier:** `standard`
     - **Item Category:** `accessories`
     - **Reason:** `wrong_item`
   - Click **Run Agent Decision**.
6. **Step 8: Execution Gate (Auto-Execution)**
   - **Show Output on Screen:**
     - Decision: **`approve`**
     - Confidence: **`0.90`** (High)
     - Matched Rule: `days_since_purchase <= 30`
     - Risk Classification: **`LOW`** (under $\$100$ threshold)
     - Status: **`Auto-Executed`** directly.
7. **Step 9: Audit Trail (`/audit`)**
   - Click on **Audit Log** in the sidebar.
   - Show the evaluator the timestamped entry capturing the case intake, decision evaluation, and tool payload.

---

### 🔹 Part B: Bounded Autonomy & Human Approval Flow (~2.5 min)

*Use Process:* **`refund_handling`** | *Fixture:* **`fx-005`** (Enterprise high-value defect claim)

1. **Submit High-Risk Case (`/cases`):**
   - In **Case Runner**, input:
     - **Days Since Purchase:** `50`
     - **Order Value ($):** `1500`
     - **Customer Tier:** `enterprise`
     - **Item Category:** `hardware`
     - **Reason:** `product_defect`
   - Click **Run Agent Decision**.
2. **Show the Risk Gate in Action:**
   - Decision: **`requires_approval`**
   - Risk Level: **`HIGH`** (exceeds $\$500$ approval threshold).
   - *Say:* *"Notice the agent does not blindly execute. It recognizes that a $\$1500$ claim exceeds the autonomous threshold and automatically halts, routing the request to the human approval queue."*
3. **Approve in the Human Review Center (`/approvals`):**
   - Click on **Approvals** in the sidebar.
   - Click on the pending approval request.
   - Show the evaluator the case details, policy citation, and the proposed action diff.
   - Click **Approve**.
4. **Demonstrate Real External Tool Execution:**
   - Point out that the tool execution runs **only after human authorization**.
   - *(Optional live proof)* Open your GitHub repository `aswa2212/OKI` Issue #1 in another browser tab to show the automated comment created live via GitHub REST API.

---

### 🔹 Part C: Domain Generalization Proof (~2 min)

*Demonstrate that OKI is a general platform, not a single-purpose refund script.*

1. **Incident Triage Case (`fx-007`):**
   - In **Case Runner**, select Process: `incident_triage`.
   - Inputs:
     - **Error Type:** `auth_failure`
     - **Affected Users Count:** `1`
     - **System Component:** `auth_service`
     - **Severity Signal:** `isolated`
   - Click **Run Agent Decision**.
   - **Result:** Decision: **`approve`** | Confidence: **`0.85`** | Matched: `affected_users <= 100` (SEV4 auto-triage).
2. **Pricing Exceptions Case (`fx-009`):**
   - Select Process: `pricing_exceptions`.
   - Inputs:
     - **Discount Percent (%):** `8`
     - **Deal Size ($):** `5000`
     - **Requestor Role:** `sales_rep`
   - Click **Run Agent Decision**.
   - **Result:** Decision: **`approve`** | Confidence: **`0.90`** | Matched: `discount_percent <= 10` (Standard sales discount).
3. **Skills Generalization:**
   - Return to **Skills Browser** (`/skills`) and switch between `incident_triage`, `pricing_exceptions`, and `refund_handling` to show that all 3 domains maintain their own independent, compiled YAML rule sets.

---

### 🔹 Part D: Empirical Evaluation & Database Verification (~1.5 min)

1. **4-Strategy Ablation Benchmark (`/evaluation`):**
   - Click on **Evaluation** in the sidebar.
   - Present the 4-Strategy comparison table:
     - **OKI Agent (Weighted Resolver):** **`100.0%` Decision Accuracy** ($10/10$ test fixtures).
     - **Most-Recent-Wins Baseline:** **`80.0%` Decision Accuracy** ($8/10$).
     - **Authority-Only Baseline:** **`80.0%` Decision Accuracy** ($8/10$).
     - **Corroboration-Only Baseline:** **`80.0%` Decision Accuracy** ($8/10$).
   - *Key Defense Statement:* *"On the 10-fixture benchmark suite, naive baselines fail on 2 critical edge cases involving genuine policy conflicts (e.g. software return ambiguity and documented enterprise exceptions). OKI's multi-factor weighted resolver correctly resolves both."*
2. **Database Inspector in Terminal:**
   - Open your terminal and run:
     ```bash
     python scripts/view_database.py
     python scripts/view_database.py decisions
     ```
   - Show the evaluator the 9 database tables in [`oki.db`](file:///C:/PROJECT%20WORKS/OKI/oki.db) updating in real time.

---

## 4. Summary Table of Exact Demo Values (Cheat Sheet)

Keep this table handy during the live demo:

| Case ID | Process | Key Inputs | Expected Decision | Exact Confidence | Risk Level | Expected Action |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **`fx-004`** | `refund_handling` | `days: 5, value: $35, tier: standard` | **`approve`** | **`0.90`** | **`LOW`** | Auto-executed |
| **`fx-005`** | `refund_handling` | `days: 50, value: $1500, tier: enterprise, defect: True` | **`requires_approval`** | **`0.90`** | **`HIGH`** | Escalated $\rightarrow$ Approved in UI |
| **`fx-007`** | `incident_triage` | `error: auth_failure, users: 1, signal: isolated` | **`approve`** | **`0.85`** | **`LOW`** | Auto-executed (SEV4 triage) |
| **`fx-009`** | `pricing_exceptions`| `discount: 8%, size: $5000, role: sales_rep` | **`approve`** | **`0.90`** | **`LOW`** | Auto-executed (Standard discount) |
