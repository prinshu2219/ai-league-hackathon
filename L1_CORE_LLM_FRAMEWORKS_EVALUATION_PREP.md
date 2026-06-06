# Core LLM Frameworks — Easy Prep Guide (Q&A Style)
### For voice interview · Use your **News Classifier** project as the example

> This is **not a coding test**. They ask questions → you explain what you built in **simple, clear words**.
> Yash lost points by being **vague**. You win by being **specific** (exact paths, exact model names, exact retry strategy).

---

## Start Here — Your 30-Second Intro

Say this first when they ask about your project:

> "I built a **News Classifier**. User sends a headline + article text. My app sends it to an LLM and returns **category** (politics, sports, tech, business), **confidence**, and a **short summary**.
>
> I use **OpenAI gpt-4o-mini** as main model, **Anthropic Claude** as backup, and sometimes a **smaller domain model** for cheap bulk classification.
>
> API keys stay in **`.env` on my laptop** and **AWS Secrets Manager in production**. If the API is busy (429 error), I **retry with exponential backoff** — wait 1s, then 2s, then 4s. Long articles get **shortened or split** so they fit the context window."

---

# PART 1 — Using OpenAI & Anthropic SDKs
### (Yash scored ~3/5 here — couldn't remember exact answer without a hint)

---

## Simple idea first

Think of calling an LLM like **ordering food**:

1. **Create a client** = open the restaurant app (connect with your API key)
2. **Write messages** = tell them what you want (system = rules, user = your actual article)
3. **Get response** = food arrives in a **box** — you must know **which compartment** to open to get the text

Yash said "the text is in content somewhere." That's too vague. You must say the **exact path**.

---

## Q1: How do you set up the OpenAI client and API key?

**Simple answer:**

> "I create an OpenAI client once at startup. The API key comes from an environment variable — never hardcoded in code. Locally I use a `.env` file. In production I load it from AWS Secrets Manager."

**Code snippet — client setup (local `.env`):**
```python
import os
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()  # reads .env file into environment

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Fail fast if key missing
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not set")
```

**Also say:** "Same pattern for Anthropic — `Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))`."

---

## Q2: How do you structure messages (system vs user)?

**Simple answer:**

> "**System message** = instructions for the model — like a job description. 'You are a news classifier. Return JSON with category and confidence.'
>
> **User message** = the actual data — the headline and article body I want classified.
>
> System sets the rules. User sends the content."

**Code snippet — messages structure:**
```python
headline = "India wins cricket series"
body = "The team scored 350 runs in the final match..."

messages = [
    {
        "role": "system",
        "content": (
            "You are a news classifier. "
            "Classify into: politics, sports, tech, business. "
            "Return JSON with category, confidence, summary."
        ),
    },
    {
        "role": "user",
        "content": f"Headline: {headline}\n\nBody: {body}",
    },
]
```

**Extra (if they ask):** Assistant role is for the model's previous replies — used in chat history, not usually on the first call.

---

## Q3: How do you get the text back from OpenAI? ⭐ MOST IMPORTANT

**This is the question Yash failed.** Memorize this exact line:

> **`response.choices[0].message.content`**

**Say it like this:**

> "OpenAI returns a response object. The generated text is at **`response.choices[0].message.content`**. 
> - `choices` = list of possible answers (usually 1)
> - `[0]` = first answer
> - `.message` = the message object
> - `.content` = the actual text string"

**Code snippet — full OpenAI SDK call (News Classifier):**
```python
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0,
    response_format={"type": "json_object"},   # force JSON output
    messages=[
        {"role": "system", "content": "Classify news. Return JSON: category, confidence, summary."},
        {"role": "user",   "content": f"Headline: {headline}\n\nBody: {body}"},
    ],
)

# ⭐ MEMORIZE THIS LINE — this is what Yash couldn't recall
text = response.choices[0].message.content

# Convert JSON string → Python dict
result = json.loads(text)
# result = {"category": "sports", "confidence": 0.95, "summary": "..."}

# Bonus fields you can mention in interview:
finish_reason = response.choices[0].finish_reason  # "stop" or "length"
tokens_used   = response.usage.total_tokens
```

**Real code from your Travel Agent** (`travel-agent/app/agents/__init__.py`):
```python
def gpt4o(system: str, user: str, temperature: float = 0.3) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)
```

---

## Q4: How is Anthropic different from OpenAI?

**Simple answer:**

| | OpenAI | Anthropic |
|--|--------|-----------|
| Get text | `response.choices[0].message.content` | `message.content[0].text` |
| System prompt | Inside `messages` list as `"role": "system"` | Separate `system=` parameter |
| Response shape | `choices[0].message` | `content` is a **list** of blocks |

**Say this:**

> "Anthropic puts the system prompt outside the messages array. And the answer text is at **`message.content[0].text`** — not `choices[0].message.content`."

**Code snippet — full Anthropic SDK call (fallback provider):**
```python
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    temperature=0,
    # ⭐ system is SEPARATE — not inside messages list
    system="Classify news into politics, sports, tech, business. Return JSON.",
    messages=[
        {"role": "user", "content": f"Headline: {headline}\n\nBody: {body}"},
    ],
)

# ⭐ MEMORIZE THIS LINE — different from OpenAI!
text = message.content[0].text

result = json.loads(text)
input_tokens  = message.usage.input_tokens
output_tokens = message.usage.output_tokens
```

**Side-by-side — extraction paths:**
```python
# OpenAI
openai_text = response.choices[0].message.content

# Anthropic
anthropic_text = message.content[0].text

# LangChain ChatOpenAI
langchain_text = llm_result.content
```

---

## Q5: What models do you use? (Don't be vague)

**Bad:** "We use GPT and Claude."

**Good:**

| Job | Model | Why |
|-----|-------|-----|
| Main classification | `gpt-4o-mini` | Cheap, fast, good enough |
| Hard / ambiguous articles | `gpt-4o` or `claude-3-5-sonnet-20241022` | Smarter |
| Bulk cheap routing | Small domain model (e.g. HuggingFace) | Very cheap at scale |
| Embeddings (if needed) | `text-embedding-3-small` | Separate from chat model |

**Terminology fix:**
- ❌ "Parenting model" → ✅ **Parent model** = the base model before you fine-tune it (e.g. Llama-3 as parent of your custom classifier)

---

## Q6: What is a domain-specific LLM?

**Simple answer:**

> "A model trained or fine-tuned for one job — like classifying news. Instead of calling expensive GPT for every article, I can route easy ones through a smaller model and only send tricky ones to GPT-4o."

**Code snippet — domain model (HuggingFace / local):**
```python
from transformers import pipeline

# Small model fine-tuned for news classification — cheap at scale
classifier = pipeline("text-classification", model="your-news-model")

result = classifier(f"{headline}. {body}")[0]
# result = {"label": "SPORTS", "score": 0.89}

# Route logic: easy/high-confidence → domain model, else → GPT-4o
if result["score"] > 0.85:
    category = result["label"]
else:
    category = classify_with_openai(headline, body)["category"]
```

---

## Q7: LangChain vs raw SDK — when do you use which?

**Simple answer:**

| Use **raw SDK** (OpenAI library directly) | Use **LangChain** |
|-------------------------------------------|-------------------|
| One simple API call | Chain of steps: prompt → LLM → parse output |
| You want full control | You want reusable prompt templates |
| Health check / ping | Structured JSON output with parsers |

> "For my classifier's main flow I use **LangChain** — prompt template piped to LLM piped to output parser. For a quick fallback call or health check, **raw SDK** is fine."

---

# PART 2 — Errors, Retries, Rate Limits
### (Yash scored 3/5 — only mentioned backoff after a hint)

---

## Simple idea first

APIs fail sometimes. Good engineers **plan for failure**:

1. Article too long → **shrink it**
2. API says "slow down" (429) → **wait and retry smarter**
3. Too many users → **limit users before hitting the API**

---

## Q8: What happens when the article is too long (context window error)?

**Simple answer:**

> "Every model has a max token limit — like a max page count. If the article is too long:
> 1. **Remove junk** — HTML, ads, extra whitespace
> 2. **Keep the important part** — headline + first few paragraphs
> 3. **Split into chunks** — classify each chunk, pick the most common category (majority vote)
> 4. **Summarize first** — summarize the long article, then classify the summary"

**Say proactively:** "I check size **before** calling the LLM so I don't waste an API call."

**Code snippet — compact long article before LLM call:**
```python
MAX_CHARS = 12000  # safe limit before hitting token cap

def prepare_article(headline: str, body: str) -> str:
    # Step 1: remove HTML / extra whitespace
    clean_body = strip_html(body).strip()

    text = f"Headline: {headline}\n\nBody: {clean_body}"

    # Step 2: if still too long, keep headline + first N chars
    if len(text) > MAX_CHARS:
        text = f"Headline: {headline}\n\nBody: {clean_body[:MAX_CHARS]}..."

    return text
```

**Code snippet — chunk + majority vote (very long articles):**
```python
from collections import Counter

def classify_long_article(headline: str, body: str) -> str:
    chunks = split_into_chunks(body, size=3000)  # split every 3000 chars
    categories = []

    for chunk in chunks:
        result = classify_with_openai(headline, chunk)
        categories.append(result["category"])

    # Pick the category that appears most often
    return Counter(categories).most_common(1)[0][0]
```

---

## Q9: How do you handle rate limit errors (429)? ⭐ SAY BACKOFF FIRST

**This is where Yash lost points.** He said "wait and retry." They wanted **exponential backoff**.

**Simple explanation of exponential backoff:**

> "Instead of waiting the same 5 seconds every time, I **double the wait** after each failure:
> - Try 1 fails → wait **1 second**
> - Try 2 fails → wait **2 seconds**
> - Try 3 fails → wait **4 seconds**
> - Try 4 fails → wait **8 seconds** (cap at ~60 seconds)
>
> I also add a tiny **random delay (jitter)** so 100 users don't all retry at the exact same moment."

**Why?** OpenAI says "slow down" because too many requests hit at once. Retrying immediately makes it worse.

**Full answer to say:**

> "On 429 I retry up to 4 times with **exponential backoff and jitter**. If OpenAI still fails, I **switch to Anthropic** as fallback. I never use a fixed wait time in production."

**Code snippet — exponential backoff (manual, no library):**
```python
import time
import random
from openai import OpenAI, RateLimitError, APITimeoutError

def call_with_backoff(client, messages, max_retries=4):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                timeout=30,
            )
            return response.choices[0].message.content

        except (RateLimitError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise  # last try failed — give up or switch provider

            # 1s → 2s → 4s → 8s + random jitter (0 to 1 second)
            wait = min(2 ** attempt + random.uniform(0, 1), 60)
            print(f"Rate limited. Waiting {wait:.1f}s before retry {attempt + 2}...")
            time.sleep(wait)
```

**Code snippet — exponential backoff with `tenacity` library (cleaner):**
```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError, APITimeoutError

@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=1, max=60),  # 1s, 2s, 4s... cap 60s
    stop=stop_after_attempt(4),
)
def classify_with_openai(headline: str, body: str) -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Classify news. Return JSON."},
            {"role": "user",   "content": f"Headline: {headline}\n\nBody: {body}"},
        ],
    )
    return json.loads(response.choices[0].message.content)
```

**Code snippet — OpenAI fails → fallback to Anthropic:**
```python
def classify_article(headline: str, body: str) -> dict:
    try:
        return classify_with_openai(headline, body)
    except (RateLimitError, APITimeoutError, Exception) as e:
        print(f"OpenAI failed ({e}), falling back to Anthropic...")
        return classify_with_anthropic(headline, body)
```

---

## Q10: What is user-side rate limiting (tiers)?

**Simple answer:**

> "The LLM provider limits **our API key**. We also limit **each user** so one person can't burn our budget.
>
> Example:
> - **Free users** → 10 requests per minute
> - **Paid users** → 100 requests per minute
>
> We check this **before** calling OpenAI. If over limit, return 'try again later' — don't even hit the LLM."

**Code snippet — simple user tier rate limit:**
```python
from datetime import datetime, timedelta

# In-memory store (production would use Redis)
user_requests = {}  # {user_id: [timestamp1, timestamp2, ...]}

TIER_LIMITS = {
    "free": 10,    # 10 requests per minute
    "paid": 100,   # 100 requests per minute
}

def check_user_rate_limit(user_id: str, tier: str) -> bool:
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)

    # Get requests in last 60 seconds
    recent = [t for t in user_requests.get(user_id, []) if t > one_minute_ago]
    user_requests[user_id] = recent

    if len(recent) >= TIER_LIMITS[tier]:
        return False  # over limit — block before calling LLM

    user_requests[user_id].append(now)
    return True  # OK to proceed

# In API endpoint:
if not check_user_rate_limit(user_id, user_tier):
    return {"error": "Rate limit exceeded. Try again in 1 minute."}, 429

result = classify_article(headline, body)
```

---

## Q11: What other errors do you handle?

| Error | What it means | What you do |
|-------|---------------|-------------|
| **429** | Too many requests | Exponential backoff, then fallback provider |
| **503** | OpenAI server down | Retry 2–3 times, then switch to Anthropic |
| **Timeout** | Request took too long | Set 30s timeout, retry once |
| **401** | Bad API key | Don't retry — fix the key, alert team |
| **Context too long** | Input too big | Compact or chunk the article |
| **Bad JSON from LLM** | Model returned garbage | Retry with stricter prompt, or use Pydantic parser |

---

## Q12: What is a circuit breaker? (Bonus — sounds expert)

**Simple answer:**

> "If OpenAI fails 5 times in a row, I **stop calling it for 60 seconds** and send all traffic to Anthropic immediately. This prevents hammering a broken service."

---

# PART 3 — Secrets & Config (.env, AWS)
### (Yash scored 4/5 — mostly good, just add a bit more detail)

---

## Simple idea first

**API keys are passwords.** Never put them in git. Never hardcode them.

---

## Q13: How do you store secrets locally (development)?

**Simple answer:**

> "I use a **`.env` file** on my machine with real keys. I add **`.env` to `.gitignore`** so git never uploads it. I commit **`.env.example`** with fake placeholders so teammates know which variables to set."

**Files:**
| File | Committed to git? | Contains |
|------|-------------------|----------|
| `.env` | ❌ NO | Real API keys |
| `.env.example` | ✅ YES | Placeholder keys like `OPENAI_API_KEY=sk-your-key-here` |
| `.gitignore` | ✅ YES | Lists `.env` so git ignores it |

**Terminology fix:** ❌ "gate techno file" → ✅ **`.gitignore`**

---

## Q14: How do you store secrets in production?

**Simple answer:**

> "In production on AWS, keys live in **AWS Secrets Manager** — a secure vault. At **app startup**, my Python code uses **boto3** to fetch the secret, parse the JSON, and store keys in memory. Keys are **never baked into the Docker image**."

**Flow in plain English:**
```
App starts → boto3 calls Secrets Manager → gets JSON with keys → stores in memory → uses for LLM calls
```

**Code snippet — local `.env` setup:**
```python
# .env  (NEVER commit this file)
OPENAI_API_KEY=sk-proj-abc123...
ANTHROPIC_API_KEY=sk-ant-xyz789...
APP_ENV=development

# .env.example  (commit this — fake values only)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
APP_ENV=development

# .gitignore  (commit this)
.env
__pycache__/
```

**Code snippet — load config from env (`config.py`):**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY: str     = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str  = os.getenv("ANTHROPIC_API_KEY", "")
    APP_ENV: str            = os.getenv("APP_ENV", "development")
    PRIMARY_MODEL: str      = "gpt-4o-mini"

    @classmethod
    def validate(cls):
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if missing:
            raise ValueError(f"Missing required env vars: {missing}")

config = Config()
config.validate()  # crash at startup if key missing
```

**Code snippet — AWS Secrets Manager (production):**
```python
import boto3
import json
import os

def load_secrets_from_aws(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="ap-south-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# At app startup (production only)
if os.getenv("APP_ENV") == "production":
    secrets = load_secrets_from_aws("prod/news-classifier/llm-keys")
    os.environ["OPENAI_API_KEY"]    = secrets["OPENAI_API_KEY"]
    os.environ["ANTHROPIC_API_KEY"] = secrets["ANTHROPIC_API_KEY"]
else:
    load_dotenv()  # local development
```

---

## Q15: What if a key is missing when the app starts?

**Simple answer:**

> "The app **crashes immediately with a clear error** — 'OPENAI_API_KEY not set'. Better to fail at startup than fail silently in the middle of a user's request."

---

## Q16: Any other config best practices?

**Say 2–3 of these:**

- All settings in one **`config.py`** file — reads from env only
- Different secrets for **dev vs prod** (separate Secrets Manager entries)
- **Feature flags** via env: `USE_ANTHROPIC_FALLBACK=true`
- **Never log API keys** — redact in logs
- ECS/Kubernetes injects env vars at deploy time

---

# PART 4 — LangChain Simple Chains
### (Yash scored 5/5 — this is your strength, keep same depth)

---

## Simple idea first

A **chain** = assembly line:

```
Prompt template  →  LLM  →  Output parser  →  Clean result
   (fill in blanks)   (think)   (format answer)
```

In LangChain you connect them with the **pipe operator `|`**:

```python
chain = prompt | llm | parser
result = chain.invoke({"headline": "...", "body": "..."})
```

---

## Q17: Walk me through your LangChain chain.

**Simple answer:**

> "Step 1: **ChatPromptTemplate** — has placeholders `{headline}` and `{body}`. System message says 'classify this news.'
>
> Step 2: **ChatOpenAI** — model `gpt-4o-mini`, temperature 0 for consistent answers.
>
> Step 3: **JsonOutputParser** with a **Pydantic model** — forces output like `{"category": "sports", "confidence": 0.95, "summary": "..."}`.
>
> I connect them: **`prompt | llm | parser`** and call **`chain.invoke({...})`**."

**Code snippet — full LangChain LCEL chain (News Classifier main path):**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Step 1: Define output shape with Pydantic
class ClassificationResult(BaseModel):
    category:   str   = Field(description="politics | sports | tech | business")
    confidence: float = Field(description="0.0 to 1.0")
    summary:    str   = Field(description="One sentence summary")

parser = JsonOutputParser(pydantic_object=ClassificationResult)

# Step 2: Prompt template with placeholders
prompt = ChatPromptTemplate.from_messages([
    ("system", "You classify news articles.\n{format_instructions}"),
    ("user",   "Headline: {headline}\n\nBody: {body}"),
])

# Step 3: LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Step 4: Connect with pipe operator
chain = prompt | llm | parser

# Step 5: Run
result = chain.invoke({
    "headline": "India wins cricket series",
    "body":     "The team scored 350 runs...",
    "format_instructions": parser.get_format_instructions(),
})

print(result)
# {"category": "sports", "confidence": 0.95, "summary": "India won the cricket series."}
```

**Code snippet — LangChain without parser (simple text output):**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
result = llm.invoke("Classify this: India wins cricket match")

text = result.content   # ⭐ LangChain extraction path
```

**Real code from Claim Verifier** (`claim-verifier/rag_engine/agent.py`):
```python
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))

llm = get_llm()
verdict_response = llm.invoke(verification_prompt_text)
raw_verdict = verdict_response.content   # ← get text here
```

---

## Q18: What is the pipe operator `|` in LangChain?

**Simple answer:**

> "It connects steps left to right — output of step 1 goes into step 2. Like a pipeline. I can add a new step (e.g. summarizer) by adding another `| summarizer` without rewriting everything."

---

## Q19: What is LCEL?

**Simple answer:**

> "**LCEL** = LangChain Expression Language. It's the modern way to build chains using the pipe operator. Same idea: `prompt | llm | parser`. Runnable, composable, easy to test."

---

## Q20: What is a RunnableParallel / runnable map?

**Simple answer:**

> "Run **two chains at the same time** on the same input. Example: classify the article **and** detect sentiment in parallel, then combine results. Saves time vs doing them one after another."

**Code snippet — RunnableParallel (classify + sentiment at same time):**
```python
from langchain_core.runnables import RunnableParallel
from langchain_core.output_parsers import StrOutputParser

classify_chain = prompt | llm | parser
sentiment_chain = sentiment_prompt | llm | StrOutputParser()

# Run both in parallel on same input
parallel_chain = RunnableParallel(
    classification=classify_chain,
    sentiment=sentiment_chain,
)

result = parallel_chain.invoke({
    "headline": "Stock market crashes",
    "body":     "Markets fell 5% today...",
    "format_instructions": parser.get_format_instructions(),
})

# result = {
#   "classification": {"category": "business", "confidence": 0.9, ...},
#   "sentiment": "negative"
# }
```

---

## Q21: How do you get structured output (not free text)?

**Simple answer:**

> "I define a **Pydantic model** with fields: category, confidence, summary. The **JsonOutputParser** tells the LLM the exact JSON shape. Parser validates the response. If parsing fails, I retry once with a stricter prompt."

**Compare to Claim Verifier:** "Claim Verifier uses regex to parse verdicts. For the classifier I use Pydantic — cleaner and more reliable."

---

## Q22: When LangChain vs raw OpenAI SDK?

**Simple answer:**

> "**LangChain** when I need prompt templates, parsers, and might add steps later.
> **Raw SDK** when it's one simple call and I want minimal dependencies.
> My classifier uses LangChain for the main path; raw SDK for fallback health checks."

---

# PART 5 — ALL CODE SNIPPETS IN ONE PLACE (Quick Review)

Copy this section before the interview. Every SDK call in one block.

```python
# ═══════════════════════════════════════════════════════════
# 1. OPENAI — full classify call
# ═══════════════════════════════════════════════════════════
import os, json, time, random
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
import anthropic

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "Classify news. Return JSON: category, confidence, summary."},
        {"role": "user",   "content": f"Headline: {headline}\n\nBody: {body}"},
    ],
)
openai_text = response.choices[0].message.content   # ⭐ MEMORIZE
result = json.loads(openai_text)


# ═══════════════════════════════════════════════════════════
# 2. ANTHROPIC — fallback provider
# ═══════════════════════════════════════════════════════════
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

message = anthropic_client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system="Classify news. Return JSON.",
    messages=[{"role": "user", "content": f"Headline: {headline}\n\nBody: {body}"}],
)
anthropic_text = message.content[0].text              # ⭐ MEMORIZE (different from OpenAI!)
result = json.loads(anthropic_text)


# ═══════════════════════════════════════════════════════════
# 3. LANGCHAIN — LCEL chain
# ═══════════════════════════════════════════════════════════
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    category: str; confidence: float; summary: str

parser = JsonOutputParser(pydantic_object=ClassificationResult)
prompt = ChatPromptTemplate.from_messages([
    ("system", "Classify news.\n{format_instructions}"),
    ("user", "Headline: {headline}\n\nBody: {body}"),
])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
chain = prompt | llm | parser                         # ⭐ pipe operator

result = chain.invoke({"headline": headline, "body": body,
                       "format_instructions": parser.get_format_instructions()})


# ═══════════════════════════════════════════════════════════
# 4. EXPONENTIAL BACKOFF on 429
# ═══════════════════════════════════════════════════════════
def call_with_backoff(messages, max_retries=4):
    for attempt in range(max_retries):
        try:
            r = openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            return r.choices[0].message.content
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** attempt + random.uniform(0, 1), 60)  # 1s, 2s, 4s, 8s
            time.sleep(wait)


# ═══════════════════════════════════════════════════════════
# 5. PROVIDER FALLBACK — OpenAI → Anthropic
# ═══════════════════════════════════════════════════════════
def classify(headline, body):
    try:
        return json.loads(call_with_backoff([...]))
    except Exception:
        return json.loads(anthropic_text)   # call Anthropic instead


# ═══════════════════════════════════════════════════════════
# 6. SECRETS — local vs production
# ═══════════════════════════════════════════════════════════
# Local:  load_dotenv()  →  os.getenv("OPENAI_API_KEY")
# Prod:   boto3.client("secretsmanager").get_secret_value(SecretId="prod/news-classifier")
# Never:  hardcode sk-... in source code
```

---

# PART 6 — Quick Memory Cards (Read Before Interview)

### Card 1 — OpenAI text extraction ⭐
```
response.choices[0].message.content
```

### Card 2 — Anthropic text extraction
```
message.content[0].text
```

### Card 3 — LangChain text extraction
```
result.content
```

### Card 4 — Exponential backoff
```
Wait: 1s → 2s → 4s → 8s (max ~60s) + small random jitter
Max 4 retries → then switch to Anthropic
```

### Card 5 — Secrets
```
Local:  .env (gitignored) + .env.example (committed)
Prod:   AWS Secrets Manager + boto3 at startup
Never:  hardcode keys in code or Docker image
```

### Card 6 — LangChain chain
```
chain = prompt | llm | parser
result = chain.invoke({variables})
```

---

# PART 7 — What NOT to Say (Yash's Mistakes)

| ❌ Don't say | ✅ Say instead |
|-------------|----------------|
| "The text is in the response somewhere" | `response.choices[0].message.content` |
| "We use GPT" | `gpt-4o-mini` for classification |
| "We wait and retry" | Exponential backoff: 1s, 2s, 4s with jitter |
| "Parenting model" | Parent model (base model before fine-tuning) |
| "Gate techno file" | `.gitignore` |
| Wait for them to hint about backoff | **Volunteer** backoff in your first answer on errors |

---

# PART 8 — 5-Minute Practice Plan

1. **Read Card 1 ten times** — OpenAI extraction path
2. **Say your 30-second intro** out loud 3 times
3. **Answer Q3, Q9, Q13, Q17** without looking — these are the most likely deep questions
4. **Skim Claim Verifier** — you can say "same ChatOpenAI pattern in my fact-checker project"
5. **Skim Travel Agent `gpt4o()`** — proof you know raw SDK extraction

---

# PART 9 — What's Implemented in News Classifier (Complete Evidence)

All features below exist in `news-classifier/` — cite these files in your interview.

| Feature | Status | File |
|---------|--------|------|
| Raw OpenAI SDK | ✅ | `app/llm/openai_client.py` |
| `response.choices[0].message.content` | ✅ | `openai_client.py` line 57 |
| Anthropic fallback | ✅ | `app/llm/anthropic_client.py` |
| `message.content[0].text` | ✅ | `anthropic_client.py` line 38 |
| LangChain LCEL chain | ✅ | `app/llm/chain.py` — `prompt \| llm \| parser` |
| Pydantic structured output | ✅ | `app/models.py` + `chain.py` |
| Exponential backoff (429) | ✅ | `openai_client.py` — `2 ** attempt + jitter` |
| Provider fallback OpenAI→Anthropic | ✅ | `app/llm/classifier.py` |
| User tier rate limits | ✅ | `app/rate_limiter.py` — free 10 RPM, paid 100 RPM |
| Context compaction | ✅ | `app/text_utils.py` |
| Chunk + classify long articles | ✅ | `app/llm/classifier.py` |
| Circuit breaker | ✅ | `app/circuit_breaker.py` |
| Domain router (cheap pre-filter) | ✅ | `app/llm/domain_classifier.py` |
| `.env` + `.env.example` + validate | ✅ | `app/config.py`, `app/secrets.py` |
| AWS Secrets Manager (prod) | ✅ | `app/secrets.py` — boto3 |
| FastAPI REST API | ✅ | `app/api.py` — POST `/classify` |
| Streamlit UI | ✅ | `app_ui.py` |
| Offline tests (no API key) | ✅ | `tests/test_offline.py` |

**Run before interview:**
```bash
cd news-classifier
python tests/test_offline.py          # offline — no keys needed
uvicorn app.api:app --port 8000       # start API
streamlit run app_ui.py               # demo UI
python scripts/run_demo.py            # live classify (needs .env key)
```

**Cross-reference with other projects:**

| Feature | News Classifier | Travel Agent | Claim Verifier |
|---------|----------------|-------------|----------------|
| Raw OpenAI SDK | ✅ | ✅ | ❌ |
| LangChain | ✅ | ❌ | ✅ |
| Exponential backoff | ✅ | ❌ | ❌ |
| Rate limits | ✅ | ❌ | ❌ planned |
| AWS Secrets Manager | ✅ code | ❌ | ❌ |

---

# Your Complete 60-Second Answer (All Topics Combined)

Practice this once before the interview:

> "I built a news classifier. User sends headline and body. A LangChain chain — prompt template, gpt-4o-mini, JsonOutputParser — returns category, confidence, and summary.
>
> I initialize OpenAI with `OpenAI(api_key=os.getenv('OPENAI_API_KEY'))`. Messages have a system role for rules and user role for the article. The answer text is at **`response.choices[0].message.content`**. Anthropic is different — **`message.content[0].text`**.
>
> Keys live in `.env` locally with `.gitignore`, and AWS Secrets Manager in prod via boto3 at startup.
>
> On errors: long articles get compacted or chunked. On 429 I use exponential backoff — 1, 2, 4, 8 seconds with jitter — max 4 tries, then fallback to Claude. Users have tier limits — 10 requests per minute free, 100 paid — checked before we call the LLM.
>
> I use LangChain for the pipeline because of the pipe operator and structured parsing. Raw SDK for simple one-off calls."

---

Good luck. **Be specific, not vague.** That is the whole difference between 3/5 and 5/5.
