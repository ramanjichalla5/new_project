# Support assistant

Run from the repository root after installing the consolidated requirements:

```bash
python -m uvicorn support_assistant.main:app --host 127.0.0.1 --port 7860
docker build -f support_assistant/Dockerfile -t zepto-support .
docker run --rm -p 7860:7860 zepto-support
```

## Architecture

1. **Ingestion:** `rag.py:Engine.__init__` reads exactly eight UTF-8 files in docs/, verbatim from the assignment. Each complete policy is one chunk; IDs doc_01 through doc_08 preserve provenance.
2. **Embedding:** SentenceTransformer `all-MiniLM-L6-v2` runs locally on CPU. It embeds each chunk into normalized vectors and upserts them into persistent Chroma collection `zepto-policies-minilm-v1`, configured for cosine distance. Upsert prevents duplicate chunks on restart; stale IDs are removed. The public model must be downloaded once; embedding inference itself requires no API, account, or network.
3. **Routing and retrieval:** The TypedDict-backed LangGraph StateGraph starts at classify_intent. In default mock mode it checks exactly the required lowercase substrings: delivery, return, refund, membership, tracking, cancel, gift card, support hours. A conditional edge sends policy_question to retrieve_and_answer and general_question to direct_answer. The policy node embeds the query locally and requests the top three cosine matches from Chroma. The general node performs no retrieval. The assignment's exact heuristic has limited recall: a policy question lacking those substrings is intentionally routed as general.
4. **Generation:** retrieve_and_answer emits `Based on the retrieved context: ` plus the first 200 characters of the single top chunk in mock mode, with all three retrieved IDs as sources. direct_answer returns `I can only answer questions about Zepto policies right now.` with empty sources. These deterministic strings make no LLM calls. Confidence is the required fixed 1.0, not a calibrated probability; excerpts can end mid-sentence.
5. **Validation and serving:** The Answer Pydantic model enforces answer:string, sources:list[string], and finite confidence in [0,1]. main.py starts the engine once through FastAPI lifespan; POST /ask accepts a nonblank query of at most 2000 characters. GET /health reports readiness, corpus count, and mock status. Inference is serialized to bound CPU/memory concurrency for the demo.

## Modes and configuration

`MOCK_LLM` unset or `1` is the graded default. `MOCK_LLM=0` branches inside all three nodes: intent classification and both answer-generation steps call the optional provider. Retrieval and graph routing remain structurally identical. `prompt.md` supplies the role/context/task/format/length template with an explicit negative constraint and few-shot example for real policy generation. Real JSON output is validated with one initial attempt and at most two corrective retries. Exhaustion returns `ERROR: ...`, empty sources, and confidence 0.0. Unsupported source IDs are rejected.

For the optional provider path, set GROQ_API_KEY and a currently available GROQ_MODEL in the environment. Provider availability and free-tier quotas are external; this extension is not required and has not been exercised against a live account. The retry tests simulate invalid outputs and recovery without transmitting a key. No secrets belong in Git.

`HF_HOME` changes the public-model cache. After downloading, `HF_HUB_OFFLINE=1` forces cache-only operation. `EMBEDDING_MODEL` can point to a local saved MiniLM directory. `CHROMA_PATH` defaults to runtime/chroma. The Dockerfile fetches and saves MiniLM during build, sets the local path and offline flags at runtime, and runs as a non-root user. Its build context is the repository root, not this subfolder.

## Deployment

Container validation passed on Linux in [GitHub Actions](https://github.com/ramanjichalla5/new_project/actions/runs/36155416030): image build, non-root startup, health check, policy retrieval, and general routing all succeeded with `docker run --network none`. All 11 integration/unit tests also passed locally and in Linux CI.

Only this module is intended for AWS deployment, after project verification. deploy.py uses an existing local AWS profile and SSM-managed Linux instance in eu-central-1. See the root README for prerequisites and command. It creates no instances or public firewall rules. No host IP is claimed until the live service is deployed and verified externally.

## Executed examples

Both calls ran against local Uvicorn with MOCK_LLM=1 and HF_HUB_OFFLINE=1. Embeddings were real and used the downloaded local model.

Health: `{"status": "ok", "documents": 8, "mock_llm": true}`

POST /ask — HTTP 200

Request:
```json
{"query": "What is the standard delivery fee?"}
```

Response:
```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard del",
  "sources": [
    "doc_01",
    "doc_02",
    "doc_03"
  ],
  "confidence": 1.0
}
```

POST /ask — HTTP 200

Request:
```json
{"query": "What is two plus two?"}
```

Response:
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```
