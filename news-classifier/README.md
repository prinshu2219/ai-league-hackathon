# News Classifier

AI news article classifier for **L1 Core LLM Frameworks** interview evidence.

Classifies headlines + body into **politics | sports | tech | business** using:
- **LangChain LCEL** chain (`prompt | llm | parser`)
- **Raw OpenAI SDK** with `response.choices[0].message.content`
- **Anthropic fallback** with `message.content[0].text`
- **Exponential backoff** on 429/timeout
- **Domain router** (cheap keyword pre-filter)
- **User tier rate limits** (free 10 RPM, paid 100 RPM)
- **Context compaction** for long articles
- **Circuit breaker** after consecutive OpenAI failures
- **`.env` local** + **AWS Secrets Manager** production

## Quick Start

```bash
cd news-classifier
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your OPENAI_API_KEY

# Run offline tests (no API key needed)
python tests/test_offline.py

# Start API
uvicorn app.api:app --reload --port 8000

# Start UI (separate terminal)
streamlit run app_ui.py

# Live demo with API key
python scripts/run_demo.py
```

## Project Structure

```
news-classifier/
├── app/
│   ├── api.py                  # FastAPI — POST /classify, rate limits
│   ├── config.py               # All env vars, validate() at startup
│   ├── secrets.py              # .env local + AWS Secrets Manager prod
│   ├── rate_limiter.py         # Free/paid tier RPM limits
│   ├── circuit_breaker.py      # Open circuit after 5 OpenAI failures
│   ├── text_utils.py           # HTML strip, compact, chunk
│   ├── models.py               # Pydantic request/response models
│   └── llm/
│       ├── chain.py            # LangChain LCEL: prompt | llm | parser
│       ├── openai_client.py    # Raw SDK + exponential backoff
│       ├── anthropic_client.py # Fallback provider
│       ├── domain_classifier.py # Cheap keyword router
│       └── classifier.py       # Main orchestrator
├── app_ui.py                   # Streamlit demo UI
├── scripts/run_demo.py
├── tests/test_offline.py       # 7 offline tests, no API keys
└── L1 prep: ../L1_CORE_LLM_FRAMEWORKS_EVALUATION_PREP.md
```

## Interview Talking Points — File Map

| Topic | File to cite |
|-------|-------------|
| OpenAI SDK + extraction | `app/llm/openai_client.py` line `response.choices[0].message.content` |
| Anthropic fallback | `app/llm/anthropic_client.py` line `message.content[0].text` |
| LangChain LCEL chain | `app/llm/chain.py` — `prompt \| llm \| parser` |
| Exponential backoff | `app/llm/openai_client.py` — `2 ** attempt + jitter` |
| Rate limits | `app/rate_limiter.py` + `app/api.py` |
| Secrets local/prod | `app/secrets.py` + `app/config.py` |
| Context window | `app/text_utils.py` — compact + chunk |
| Circuit breaker | `app/circuit_breaker.py` |

## API

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "India wins cricket series",
    "body": "The team scored 350 runs.",
    "user_id": "user-1",
    "tier": "free",
    "use_chain": true
  }'
```

## Tests

```bash
python tests/test_offline.py
# 7 test classes: domain router, text utils, rate limiter, circuit breaker, config, chain
```
