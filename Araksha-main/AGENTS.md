# AGENTS.md: Ground Rules

These ground rules apply to every task and stage in the Silent Node development pipeline:

1. **No Data Leakage (Highest Priority)**:
   - Never use data that would not have been available at the forecast origin week $t$.
   - Treat the most recent 2 weeks of case data as incomplete due to reporting lags.
   - Leakage is the top bug to avoid. Any feature, lag, or parameter threshold calculated using future data ($> t$) violates protocol.

2. **No Invented or Silently Interpolated Data**:
   - Never invent, interpolate silently, or hard-code data.
   - Every number in a report or chart must be computed by code from files in the repo.
   - Report any gaps explicitly instead of silently filling them.

3. **Strict Handling of Missing or Stale Inputs**:
   - Missing or stale inputs are never defaulted to low risk.
   - They must explicitly produce the tier `'Insufficient Data'`.

4. **Reproducible Caching and Ingestion Logging**:
   - Cache raw downloads in `data/raw/` (git-ignored for heavy payloads).
   - Cleaned, normalized tables reside in `data/processed/`.
   - Log every external download with URL and UTC timestamp.

5. **Pinning, Seeds, and Unit Testing**:
   - Pin dependency versions in `pyproject.toml` / `package.json`.
   - Set random seeds for all stochastic procedures.
   - Write unit tests for each module (validation, WIS calculation, leakage prevention).

6. **Modular Design & Single Responsibility**:
   - Small modules, explicit type hints, concise docstrings, clear interfaces.
   - Keep evaluation honest: do not tune models on the test window (2022-2026).
   - If an ablation or model loses to the baseline, report the loss truthfully without hiding numbers.
