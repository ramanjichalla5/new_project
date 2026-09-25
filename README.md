# Zepto Data & AI Platform

One educational platform with three capabilities: a catalogue pipeline supplies relational data, an analytics pipeline demonstrates reproducible modeling, and a grounded policy assistant exposes FastAPI. Titanic is a passenger-outcome example, not Zepto customer data. Policy documents are the supplied assignment corpus, not verified current commercial policies.

## Setup

Use **Python 3.12** and the **single consolidated root requirements.txt** for all modules. Internet is required initially for packages, scraping, Titanic, and the public embedding-model download. No paid API or LLM account is required.

```bash
git clone https://github.com/ramanjichalla5/new_project.git
cd new_project
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell alternative:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run all commands from the repository root. `runtime/` contains regenerable ignored artifacts.

## 1. Catalogue data pipeline

```bash
python data_pipeline/pipeline.py
```

Requests and BeautifulSoup scrape the first five pages of [Books to Scrape](https://books.toscrape.com/), opening each detail page for the actual category. Captured fields are title, listed GBP price, text rating, listed availability, and category. Malformed rows are dropped rather than inventing catalogue facts; title/category duplicates are removed. Prices are floats, ratings integers 1–5, and stock booleans. **1 GBP = 105.50 INR** is the fixed artificial baseline; no currency API is called. INR values round to two decimal places.

`runtime/catalogue.sqlite` is rebuilt with books and categories, primary/foreign keys, and CHECK constraints. [queries.sql](data_pipeline/queries.sql) contains six executed queries covering SELECT/WHERE, ORDER BY, LIMIT, DISTINCT, IN, BETWEEN, and JOIN. Every query uses `pd.read_sql`. The final JOIN is reproduced independently with `pd.merge` and equality asserted. [RESULTS.md](data_pipeline/RESULTS.md) records each query and output, dtypes, counts, and the side-by-side JOIN comparison.

## 2. Titanic analytics

```bash
python analytics/pipeline.py
python analytics/pipeline.py --offline
python analytics/predict.py
```

The pipeline calls `sns.load_dataset('titanic')` once and immediately saves [titanic.csv](analytics/titanic.csv). Profiling, cleaning, EDA, classification, and regression continue from that same in-memory cohort. The CSV is the raw fallback, not an independent modeling dataset.

Measured missingness determines strategy: under 5% drops missing rows; 5–30% imputes; severe missingness drops the field with justification. A single stratified split is established before fitting statistics. Logistic Regression, Decision Tree, and Random Forest share the split and use ColumnTransformer/Pipeline preprocessing. The report includes confusion matrices, ROC/AUC, accuracy/precision/recall/F1, baseline/balanced/SMOTE comparison, Random Forest GridSearchCV and OOB score, and fare regression with MAE/RMSE/R²/adjusted R² and residual interpretation. SMOTE fits only training rows. The saved classifier is a complete fitted pipeline and is reloaded and checked on raw inputs.

Read [RESULTS.md](analytics/RESULTS.md) for numerical outputs, chart interpretations, strongest correlations, missingness decisions, model comparison, and recommendation.

## 3. Grounded support assistant

```bash
python -m uvicorn support_assistant.main:app --host 127.0.0.1 --port 7860
```

`MOCK_LLM` defaults to `1`. LangGraph nodes `classify_intent`, `retrieve_and_answer`, and `direct_answer` route policy questions into MiniLM embeddings and top-three cosine retrieval in Chroma. Mock answers contain the first 200 characters of the top chunk; general answers use a fixed string and no sources. Confidence 1.0 is a deterministic assignment field, not calibrated certainty.

See the [support README](support_assistant/README.md) for recorded responses and ingestion → embedding → retrieval → generation architecture. [prompt.md](support_assistant/prompt.md) contains the actual role/context/task/format/length template, negative constraint, and few-shot example.

### Container

```bash
docker build -f support_assistant/Dockerfile -t zepto-support .
docker run --rm --name zepto-support -p 7860:7860 zepto-support
```

## Verification and Git workflow

```bash
python -m pytest -q
git log --graph --oneline --all
```

The feature branch `capstone/zepto-platform` carries multiple commits and is intended to satisfy the assignment's feature-branch workflow requirement.

Verified local run: 100 books across 29 categories; all six SQL queries executed and JOIN equivalence passed; Titanic EDA/modeling and raw-input reload completed; **11 tests passed**; both Uvicorn example calls returned HTTP 200. The Linux CI run also passed the tests and successfully built the Docker image and verified both API routes with container networking disabled.

## References and authorship

Official references: [scikit-learn pipelines](https://scikit-learn.org/stable/modules/compose.html), [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), and [Chroma configuration](https://docs.trychroma.com/docs/collections/configure). Review and understand the implementation and comply with your course's academic-integrity requirements before submission.
