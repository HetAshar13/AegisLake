# Contributing to AegisLake

Thank you for your interest in contributing to **AegisLake**! This document outlines our development workflows, coding standards, and testing protocols.

---

## 1. Development Environment Setup

### Prerequisites
- **Python:** 3.12+ (managed via `uv` or standard `python -m venv`)
- **Java:** JDK 17+ (required for local PySpark execution)
- **Git:** 2.40+

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/HetAshar13/AegisLake.git
cd AegisLake

# Create virtual environment and install pinned dependencies
uv venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

---

## 2. Code Quality & Formatting Standards

We enforce modern Python standards via `ruff` and `black`:
- **Python Standards:** Follow PEP 8 with explicit type hints (`typing`, `pydantic.BaseModel`, `typing.TypedDict`).
- **No Floating-Point Money:** All financial and monetary arithmetic **must** be performed using integer minor units (`BIGINT` cents, yen, or fils) and scaled strictly at the presentation layer via ISO-4217 exponents.
- **Run Linter:**
  ```bash
  uvx ruff check .
  ```

---

## 3. Running the Verification Test Suite

Every commit must maintain **100% pass rates** across our automated test suites:

### A. Run Full Pytest Suite (56 Tests)
```bash
pytest -v
```

### B. Run dbt Kimball Mart Invariant Tests (40 Tests)
```bash
cd aegis_dbt
dbt parse --profiles-dir .
dbt compile --profiles-dir .
dbt test --profiles-dir .
cd ..
```

### C. Run Infrastructure & Databricks DAB Verification Tests
```bash
pytest tests/test_iac.py tests/test_dabs.py tests/test_ci.py -v
```

---

## 4. Submitting Pull Requests

1. Fork the repo and create your feature branch: `git checkout -b feat/your-feature-name`.
2. Commit your changes using **Conventional Commits**:
   - `feat: add SEPA Instant payment rail parser`
   - `fix: correct BHD 3-decimal scaling in dim_currencies`
   - `docs: update system design playbook`
3. Ensure all CI/CD quality gates pass before opening a Pull Request against `main`.
