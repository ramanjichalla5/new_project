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

Run all commands from the repository root. `runtime/` contains regenerable ignored artifacts. File counts: data_pipeline has five files; analytics has seven; support_assistant has seven implementation/documentation files plus the eight explicitly required corpus documents under docs/. Those documents are the necessary exception to the requested 4–7 files per module.

## 1. Catalogue data pipeline

```bash
python data_pipeline/pipeline.py
```

Requests and BeautifulSoup scrape the first five pages of [Books to Scrape](https://books.toscrape.com/), opening each detail page for the actual category. Captured fields are title, listed GBP price, text rating, listed availability, and category. Malformed rows are dropped rather than inventing catalogue facts; title/category duplicates are removed. Prices are floats, ratings integers 1–5, and stock booleans. **1 GBP = 105.50 INR** is the fixed artificial baseline; no currency API is called. INR values round to two decimal places.

`runtime/catalogue.sqlite` is rebuilt with books and categories, primary/foreign keys, and CHECK constraints. [queries.sql](data_pipeline/queries.sql) contains six executed queries covering SELECT/WHERE, ORDER BY, LIMIT, DISTINCT, IN, BETWEEN, and JOIN. Every query uses `pd.read_sql`. The final JOIN is reproduced independently with `pd.merge` and equality asserted. [RESULTS.md](data_pipeline/RESULTS.md) records each query and output, dtypes, counts, and the side-by-side JOIN comparison. [books.csv](data_pipeline/books.csv) is the textual clean snapshot; pipeline.py is the exact database-regeneration deliverable.

## 2. Titanic analytics

```bash
python analytics/pipeline.py
# Use the committed offline fallback:
python analytics/pipeline.py --offline
python analytics/predict.py
```

The pipeline calls `sns.load_dataset('titanic')` once and immediately saves [titanic.csv](analytics/titanic.csv). Profiling, cleaning, EDA, classification, and regression continue from that same in-memory cohort. The CSV is the raw fallback, not an independent modeling dataset.

Measured missingness determines strategy: under 5% drops missing rows; 5–30% imputes; severe missingness drops the field with justification. A single stratified split is established before fitting statistics. EDA fills age with the training median; the original missing-age mask is preserved. Modeling restores only that mask on the same cleaned cohort, allowing each training/CV fold to learn its own imputer. Full-frame EDA z-scores never feed modeling. `alive` leaks the label; redundant derived features are excluded.

Logistic Regression, Decision Tree, and Random Forest share the split and use ColumnTransformer/Pipeline preprocessing. The report includes confusion matrices, ROC/AUC, accuracy/precision/recall/F1, baseline/balanced/SMOTE comparison, three-parameter Random Forest GridSearchCV and OOB score, and fare regression with MAE/RMSE/R²/adjusted R² and residual interpretation. SMOTE fits only training rows. The saved classifier maximizes training CV F1, not test performance; its entire fitted pipeline is saved to `runtime/best_pipeline.joblib`, reloaded, and checked on raw inputs.

Read [RESULTS.md](analytics/RESULTS.md) for all numerical outputs, four chart interpretations, the two strongest correlations, missingness decisions, model comparison, and recommendation. [charts.png](analytics/charts.png) consolidates plots; [tree.png](analytics/tree.png) is the readable labeled tree. Written interpretations remain sufficient for assessment.

## 3. Grounded support assistant

```bash
python -m uvicorn support_assistant.main:app --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860/docs`; readiness is `GET /health`. `MOCK_LLM` defaults to `1`. LangGraph nodes classify_intent, retrieve_and_answer, and direct_answer route policy questions into real MiniLM embeddings and top-three cosine retrieval in Chroma. Mock answers contain the first 200 characters of the top chunk and three source IDs; general answers use a fixed string and no sources. Confidence 1.0 is a deterministic assignment field, **not** calibrated certainty.

```bash
curl -X POST http://127.0.0.1:7860/ask -H "Content-Type: application/json" -d '{"query":"What is the standard delivery fee?"}'
curl -X POST http://127.0.0.1:7860/ask -H "Content-Type: application/json" -d '{"query":"What is two plus two?"}'
```

See the [support README](support_assistant/README.md) for recorded responses and ingestion → embedding → retrieval → generation architecture. [prompt.md](support_assistant/prompt.md) contains the actual role/context/task/format/length template, negative constraint, and few-shot example. Optional `MOCK_LLM=0` uses environment-supplied `GROQ_API_KEY` and `GROQ_MODEL`; there is one attempt plus two corrective retries and Pydantic validation. Exhaustion returns a marked error and zero confidence. This provider path has mocked retry tests; no live LLM key is committed or needed.

### Container and AWS

```bash
docker build -f support_assistant/Dockerfile -t zepto-support .
docker run --rm --name zepto-support -p 7860:7860 zepto-support
```

The image uses CPU PyTorch, downloads MiniLM at build time, disables Hub access at runtime, runs as non-root, and has a health check. Only Module 3 is deployed. AWS deployment targets an existing Linux EC2 host in **eu-central-1**, with Docker/git/curl, an online SSM agent and instance role, at least 4 GiB RAM, sufficient image disk, and a permitted inbound TCP 7860 rule. Use an existing local AWS profile; never commit credentials. The script does not purchase resources or alter IAM/network permissions.

```bash
python support_assistant/deploy.py --profile YOUR_PROFILE --region eu-central-1 --instance i-YOUR_INSTANCE --commit FULL_PUBLISHED_COMMIT_SHA
```

The deployer pins the published revision, health-tests a candidate on loopback, switches only the named service with startup rollback, then externally checks health and both API routes before printing the host IP and writing ignored `deployment.json`. Public IP can change after instance stop/start. This HTTP demo serves only public policy text; use TLS and access/rate controls before real customer traffic. Deployment is complete only after external checks pass.

## Verification and Git workflow

```bash
python -m pytest -q
git log --graph --oneline --all
```

Tests cover malformed rows, conversion, foreign keys, idempotency, train-only transforms, raw-input reload, real retrieval for all eight documents, graph routes, request validation, and bounded LLM retries. Download MiniLM once before offline tests. The feature branch `codex/zepto-platform` carries multiple commits and is merged with a merge commit so the scored Git history remains visible.

Verified local run: 100 books across 29 categories; all six SQL queries executed and JOIN equivalence passed; Titanic EDA/modeling and raw-input reload completed; **11 tests passed**; both live Uvicorn example calls returned HTTP 200 with model-cache offline mode enabled. Container verification is handled by the GitHub Actions workflow because the local Docker engine is unavailable. AWS deployment remains pending authenticated target access.

## References and authorship

Official references: [scikit-learn pipelines](https://scikit-learn.org/stable/modules/compose.html), [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), and [Chroma configuration](https://docs.trychroma.com/docs/collections/configure). This repository was developed with AI assistance; review and understand the implementation and comply with your course's academic-integrity requirements before submission.
