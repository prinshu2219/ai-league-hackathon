# L1 RAG Fundamentals — Complete Evaluation Prep Guide
### Based on Claim Verifier codebase + official evaluation criteria

> **Purpose:** This guide prepares you for the **voice-based AI Skill Evaluation** on **RAG Fundamentals and Implementation**. It is **not a coding interview** — you need to **explain concepts, tradeoffs, and decisions** clearly, using your Claim Verifier project as your real-world example.

---

## How to Use This Guide

1. Read each section fully — understand **why**, not just **what**.
2. Practice answering the **"Likely Questions"** out loud (15 min session style).
3. For each criterion, know: **what you built → why you chose it → what you'd improve at scale**.
4. Be honest about gaps — saying *"we used semantic-only search, but in production I'd add hybrid search because..."* scores better than pretending.

---

## Your Project in One Paragraph (Memorize This)

**Claim Verifier** is an AI fact-checking system I built for the AI League Hackathon. When a user submits a claim, a **LangChain ReAct agent (GPT-4o)** gathers evidence by searching a **ChromaDB knowledge base** (pre-loaded with trusted fact-check sites, Wikipedia, BBC, ICC rankings, and curated static facts) and **live web results via Tavily**. Retrieved KB chunks go through **FlashRank reranking** for better precision. All evidence is combined with a **source credibility tier guide**, then a second **GPT-4o call** produces a structured verdict (TRUE/FALSE/PARTIALLY TRUE/NOT ENOUGH EVIDENCE) with citations. The system is exposed via a **Streamlit web app** and a **Chrome browser extension** that deep-links claims into the app. It runs in **Docker** with optional **KB growth** from web harvest results.

---

# CRITERION 1: Document Ingestion and Chunking (Target: 5/5)

## What Evaluators Are Looking For

From the scoring rubric, a **5/5** answer covers:

- A **complete ingestion pipeline** — how raw documents enter the system
- Handling **different document types** (PDF, TXT, web pages, images/OCR if applicable)
- **Preprocessing steps** — cleaning, normalization, enrichment, PII handling
- **Chunking strategy** — recursive vs agentic/LLM-based, with clear rationale
- **Chunk size and overlap** — why those numbers, not just what they are
- **Adapting chunking** as document complexity increases

---

## Core Concepts (Easy Explanation)

### What is Document Ingestion?

**Ingestion** is everything that happens **before** text goes into your vector database:

```
Raw source → Load/parse → Clean/preprocess → Chunk → Embed → Store
```

Think of it like preparing food before cooking: you don't throw a whole cabbage into the pot — you wash, peel, and chop it first.

### Why Ingestion Matters

Bad ingestion = bad retrieval forever. No amount of fancy reranking fixes:
- Garbage text from broken PDF parsing
- Chunks that cut mid-sentence and lose meaning
- Duplicate documents polluting search results
- Sensitive data (PII) leaking into LLM prompts

### Document Types and How to Handle Them

| Type | Challenge | Common Approach |
|------|-----------|-----------------|
| **Plain text (.txt)** | Minimal — already clean | Direct load |
| **Web pages (HTML)** | Navigation menus, ads, boilerplate | WebBaseLoader, BeautifulSoup, strip HTML tags |
| **PDFs** | Multi-column layout, tables, scanned images | PyPDF, pdfplumber, or OCR (Tesseract) for scanned PDFs |
| **Images** | Text is inside pixels, not selectable | OCR (Tesseract, AWS Textract, Google Vision) |
| **Structured data** | Tables, JSON — bad to chunk naively | Row-level or section-level chunking, preserve structure in metadata |

### Preprocessing Steps (Know These Even If You Didn't Build Them)

Even if Claim Verifier doesn't do all of these, **evaluators expect you to know the concepts**:

1. **Text cleaning** — Remove HTML tags, extra whitespace, headers/footers, navigation text
2. **Normalization** — Standardize dates, units, entity names (e.g., "Dr." vs "Doctor")
3. **NER (Named Entity Recognition)** — Tag people, places, organizations — useful for metadata filtering later
4. **Enrichment** — Add tags like document category, language, publication date
5. **PII masking** — Detect and redact emails, phone numbers, SSNs, patient names before storing or sending to LLM
6. **Deduplication** — Don't index the same URL/content twice (Claim Verifier does this via `url_exists_in_kb()`)

### What is Chunking?

**Chunking** = splitting long documents into smaller pieces before embedding.

**Why?**
- One 5000-word article covers many topics → one embedding gets "confused"
- Smaller chunks = more precise retrieval ("When did India ban TikTok?" hits the exact sentence)
- LLMs have context limits — you can't stuff whole documents into every prompt

### Chunking Strategies (Know Both)

#### 1. Recursive Character Splitting (What Claim Verifier Uses)

- Tries to split on **natural boundaries** in order: paragraphs → lines → sentences → words → characters
- **Predictable, fast, no API cost**
- Best for: news articles, fact-check pages, Wikipedia, general prose

**Claim Verifier settings:**
- `chunk_size = 300` characters
- `chunk_overlap = 40` characters
- Separators: `["\n\n", "\n", ". ", " ", ""]`

**Why 300 chars?** Fact-check snippets and static facts are short. Smaller chunks = more precise matching for specific claims. Tradeoff: very small chunks may lose broader context.

**Why 40 overlap?** If a sentence sits on a chunk boundary ("India banned TikTok on June 29, 2020"), overlap ensures both adjacent chunks contain enough context to be retrieved.

#### 2. Agentic / LLM-Based Chunking (Know Conceptually)

- An LLM reads the document and decides **where semantic boundaries are**
- Example: "This paragraph discusses the ban date, this one discusses the legal basis — split here"
- **Pros:** Chunks follow meaning, not character count — great for complex docs (medical records, legal contracts)
- **Cons:** Slower, costs API money, less predictable
- **When to use:** Documents where fixed-size splitting breaks logical units (multi-topic medical reports, policy documents)

#### 3. Other Strategies (Mention If Asked)

- **Fixed-size token splitting** — By tokens (512, 1024) instead of characters — better for LLM context budgeting
- **Semantic chunking** — Embed sentences, merge until similarity drops — chunks follow topic shifts
- **Document-structure-aware** — Split by headings (H1, H2) in HTML/Markdown — preserves section context

### Adapting Chunk Size to Document Complexity

This is a **5/5 differentiator**. Explain it like this:

| Document Type | Suggested Approach |
|---------------|-------------------|
| Short facts (static facts list) | No chunking needed — each fact is already one chunk |
| News articles / web pages | 300–500 chars, moderate overlap (40–80) |
| Long encyclopedia pages | 500–1000 chars, or structure-aware (by heading) |
| Medical/legal PDFs | Larger chunks (800–1500) OR agentic chunking to preserve context |
| Code documentation | Split by function/class, not character count |

**Claim Verifier example:** Static facts like "India banned TikTok on June 29, 2020" are stored as single documents — no splitting needed. Long BBC articles get recursive splitting at 300 chars.

---

## How Claim Verifier Does Ingestion (Your Talking Points)

### Pipeline Flow

```
scripts/build_knowledge_base.py
  ├── load_static_facts()     → Hand-curated facts (always loaded)
  ├── load_from_web()         → WebBaseLoader scrapes trusted URLs
  └── add_documents_to_kb()   → Chunks + embeds + stores in ChromaDB
```

### Source Types

1. **Static facts** — 11 hand-written facts (TikTok ban, Moon landing, COVID, Chandrayaan-3, ICC rankings note, etc.)
   - Metadata: `source`, `url`, `category: "static_fact"`
   - No web scraping needed — reliable baseline

2. **Trusted web sources** — Snopes, FactCheck.org, PolitiFact, Wikipedia pages, BBC News, ICC rankings
   - Loaded via `WebBaseLoader`
   - Metadata: `source`, `url`, `category` (fact-check / encyclopedia / news / sports)

3. **Optional web harvest** — After verification, Tavily results can be added back to KB
   - Controlled by env vars: `ENABLE_KB_UPDATE_FROM_WEB`, `KB_UPDATE_MAX_DOCS_PER_RUN`
   - Dedup by URL before adding
   - Category: `web_harvest`

### Chunking in Claim Verifier

- **File:** `utils/chunker.py`
- **Strategy:** RecursiveCharacterTextSplitter
- **Every path into ChromaDB goes through chunking** — build script AND web harvest

---

## What You'd Improve (Shows Production Thinking)

Be ready to say:

> "For our hackathon MVP, we used WebBaseLoader for HTML pages and recursive splitting at 300 chars. For production with PDFs or scanned documents, I'd add PyPDF/pdfplumber for PDF parsing, OCR for scanned content, PII detection before storage, and agentic chunking for complex multi-topic documents. I'd also add document-level metadata like `published_date` and `language` for filtered retrieval."

---

## Hands-On Preparation (No Code Required — Just Do These)

1. **Run the build script** and observe output: `python scripts/build_knowledge_base.py --no-web` — notice how many chunks come from 11 static facts vs full web pages
2. **Open `utils/chunker.py` and `scripts/build_knowledge_base.py`** — be able to explain every parameter without reading the file
3. **Think of 3 claims** and trace which chunk would match:
   - "India banned TikTok" → static fact chunk
   - "Who is #1 in ODI cricket?" → ICC rankings chunk
   - "Is the Earth flat?" → Snopes/fact-check chunk
4. **Practice explaining** why 300/40 is right for fact-checking but wrong for legal documents
5. **Read about** OCR, NER, PII masking conceptually (10 min each on any blog) so you can discuss them even though Claim Verifier doesn't use them

---

## Likely Interview Questions + How to Answer

**Q: Walk me through your document ingestion pipeline.**
> A: We have two ingestion paths. First, a build script loads 11 curated static facts and optionally scrapes trusted URLs — fact-check sites, Wikipedia, BBC, ICC rankings — using WebBaseLoader. Each document gets metadata: source name, URL, and category. Before storage, all documents pass through RecursiveCharacterTextSplitter with 300-char chunks and 40-char overlap, splitting on paragraph/sentence boundaries. Optionally, after live verification, we harvest up to 3 new web results into the KB with URL deduplication.

**Q: Why did you choose 300 characters for chunk size?**
> A: Our content is mostly short fact-check snippets and curated facts. Smaller chunks give precise retrieval — when someone asks about the TikTok ban date, we want the exact sentence, not a 2000-word page. The tradeoff is we might lose broader context, which is why we use 40-char overlap and reranking to surface the best chunks.

**Q: What's the difference between recursive and agentic chunking?**
> A: Recursive splitting uses fixed rules — split on paragraphs, then sentences, then words — based on character count. It's fast, free, and predictable. Agentic chunking uses an LLM to identify semantic boundaries — "this section is about diagnosis, this is about treatment." It's better for complex documents like medical records where fixed-size splits break logical units, but it's slower and costs API calls. We used recursive for our use case because our sources are news articles and short facts.

**Q: How would you handle PDFs or scanned documents?**
> A: For digital PDFs, I'd use PyPDF or pdfplumber to extract text, handling tables separately. For scanned PDFs, I'd run OCR with Tesseract or a cloud service like AWS Textract. Then apply PII masking if needed, and use larger chunk sizes or agentic chunking since medical/legal PDFs have dense, interconnected content.

**Q: How do you prevent duplicate documents?**
> A: Before adding harvested web results, we check `url_exists_in_kb()` — a metadata lookup in ChromaDB filtering by URL. We also deduplicate within a single harvest run using a seen-URLs set.

---

# CRITERION 2: Embeddings and Vector Storage (Target: 5/5)

## What Evaluators Are Looking For

A **5/5** answer covers:

- **How you chose your embedding model** — comparison/evaluation process
- **What you store** — chunk text, embeddings, metadata fields and their purpose
- **Vector database choice** and why
- **Metadata design** — concrete examples of fields and how they're used

---

## Core Concepts (Easy Explanation)

### What Are Embeddings?

An **embedding** converts text into a list of numbers (a **vector**). Similar meanings → similar vectors.

Example:
- "India banned TikTok" → `[0.12, -0.45, 0.78, ...]` (1536 numbers)
- "TikTok was banned in India" → `[0.11, -0.44, 0.79, ...]` (very close!)
- "The weather is nice today" → `[0.89, 0.23, -0.56, ...]` (far away)

This lets us find relevant chunks using **math** instead of keyword matching.

### How to Choose an Embedding Model

Evaluators want to hear you **evaluated options**, not picked randomly:

| Factor | What to Consider |
|--------|-----------------|
| **Quality** | Does it capture semantic similarity well for your domain? Test with sample queries |
| **Speed** | How fast per embedding? Matters at scale (millions of chunks) |
| **Cost** | API cost per token vs self-hosted compute |
| **Size/dimensions** | Higher dimensions = more storage, sometimes better quality |
| **Domain fit** | General vs specialized (e.g., medical, legal embeddings) |

**Evaluation approach (what a 5/5 candidate describes):**
1. Create a **test set** of 20–50 query-chunk pairs (query → expected relevant chunk)
2. Embed all chunks with 2–3 candidate models
3. Measure **recall@k** (did the right chunk appear in top 5?) and **MRR** (how high was it ranked?)
4. Compare **latency** and **cost** per 1000 embeddings
5. Pick the best tradeoff for your use case

**Models to know:**

| Model | Provider | Dimensions | Notes |
|-------|----------|------------|-------|
| text-embedding-3-small | OpenAI | 1536 | Fast, cheap, good general quality |
| text-embedding-3-large | OpenAI | 3072 | Better quality, more expensive |
| all-MiniLM-L6-v2 | Sentence Transformers | 384 | Free, local, good for prototyping |
| Cohere embed-v3 | Cohere | 1024 | Strong multilingual |
| BGE-large | BAAI | 1024 | Popular open-source option |

**Claim Verifier choice:** `text-embedding-3-small` — fast, cheap, same API key as GPT-4o, good enough for general fact-checking.

### What is a Vector Database?

A database optimized for storing vectors and finding **nearest neighbors** quickly.

**Options to know:**

| Database | Type | Best For |
|----------|------|----------|
| **ChromaDB** | Local/embedded | Prototyping, small-medium scale, no infra |
| **Pinecone** | Managed cloud | Production, auto-scaling, minimal ops |
| **OpenSearch** | Self-hosted/cloud | Hybrid search (vector + keyword), enterprise |
| **Weaviate** | Open-source/cloud | Hybrid search, GraphQL API |
| **FAISS** | Library (not DB) | Fast similarity search, no persistence built-in |
| **pgvector** | PostgreSQL extension | When you already use Postgres |

**Claim Verifier choice:** ChromaDB — local, persistent to disk at `data/chroma_db`, no separate server, perfect for hackathon/MVP.

### What to Store (The Full Picture)

For each chunk in the vector DB, store:

1. **Vector** — the embedding (list of floats)
2. **Document text** — the actual chunk content (needed for LLM prompt)
3. **Metadata** — structured fields for filtering, display, and debugging

### Metadata Design (Critical for 5/5)

**Claim Verifier metadata fields:**

| Field | Purpose | Example |
|-------|---------|---------|
| `source` | Human-readable source name | "Snopes", "Wikipedia - COVID-19" |
| `url` | Original URL for citations + dedup | "https://www.snopes.com/..." |
| `category` | Filter/group by content type | "fact-check", "encyclopedia", "news", "sports", "static_fact", "web_harvest" |
| `rerank_score` | Added at query time — relevance score | 0.8734 |

**Metadata you'd add in production:**

| Field | Purpose |
|-------|---------|
| `published_date` | Filter/recency bias for time-sensitive claims |
| `language` | Multi-language support |
| `document_id` | Link chunks back to parent document |
| `chunk_index` | Order within document (0, 1, 2...) |
| `author` | Attribution |
| `confidence_score` | OCR/parsing quality |

**Why metadata matters:** You can filter search — e.g., "only search fact-check category" or "only sources from 2024." Without metadata, you're blind.

---

## How Claim Verifier Does Embeddings + Storage (Your Talking Points)

### Embedding Model
- **File:** `utils/embeddings.py`
- **Model:** OpenAI `text-embedding-3-small` (1536 dimensions)
- **Same key** as GPT-4o — one API key for everything
- Used for both **indexing** (each chunk on insert) and **querying** (each search)

### Vector Storage
- **File:** `rag_engine/knowledge_base.py`
- **Database:** ChromaDB, collection `claim_verifier_kb`
- **Path:** `data/chroma_db/` (persists between restarts)
- **Similarity:** Cosine similarity (LangChain Chroma default)

### Key Operations
- `add_documents_to_kb()` — chunk → embed → store
- `search_knowledge_base()` — embed query → similarity search → rerank
- `url_exists_in_kb()` — metadata filter for dedup
- `get_kb_stats()` — collection count for UI sidebar

---

## What You'd Improve (Shows Production Thinking)

> "We used text-embedding-3-small for speed and cost in the MVP. For production, I'd benchmark it against text-embedding-3-large and a self-hosted model like BGE on our fact-check query set, measuring recall@5 and latency. I'd migrate to OpenSearch or Pinecone for hybrid search at scale, add metadata fields like published_date and chunk_index, and implement filtered retrieval by category."

---

## Hands-On Preparation

1. **Check KB stats** — run the app, look at sidebar "X chunks loaded"
2. **Understand dimensions** — text-embedding-3-small produces 1536-dimensional vectors; know what that means (more dims = more nuance, more storage)
3. **Practice comparing models** — even without running tests, describe HOW you'd test: "I'd create 30 claim-chunk pairs, embed with 3 models, measure recall@5"
4. **Know cosine similarity** — measures angle between vectors; 1.0 = identical direction, 0 = unrelated
5. **Explain why you store text AND vectors** — vector for search, text for LLM prompt (vector alone isn't readable)

---

## Likely Interview Questions + How to Answer

**Q: How did you choose your embedding model?**
> A: We chose OpenAI text-embedding-3-small because it's fast, cost-effective, and shares the same API key as our GPT-4o model. For a fact-checking use case with general news and encyclopedia content, it captures semantic similarity well — "India banned TikTok" matches "TikTok was prohibited in India." For production, I'd benchmark against text-embedding-3-large and open-source alternatives like BGE on a labeled test set, measuring recall@5, latency, and cost per 1000 embeddings.

**Q: Why ChromaDB over Pinecone or OpenSearch?**
> A: For our hackathon MVP, ChromaDB was ideal — it runs locally, persists to disk, needs no separate server, and integrates cleanly with LangChain. For production at scale with millions of chunks, I'd consider OpenSearch for hybrid vector+keyword search or Pinecone for managed scaling. ChromaDB was the right tradeoff for prototype speed.

**Q: What metadata do you store and why?**
> A: Each chunk has source name, URL, and category. Source and URL are critical for citations in our verdict output and for deduplication when harvesting web results. Category lets us distinguish fact-check articles from encyclopedia content from live-harvested web results. At query time, we also attach rerank_score. In production, I'd add published_date for recency filtering and document_id to reconstruct full documents from chunks.

**Q: What happens when you add a document to the knowledge base?**
> A: Documents go to add_documents_to_kb(), which first splits them via RecursiveCharacterTextSplitter, then ChromaDB embeds each chunk using text-embedding-3-small and stores the vector, text, and metadata in the claim_verifier_kb collection on disk.

---

# CRITERION 3: Retrieval and Prompt Augmentation (Target: 5/5)

## What Evaluators Are Looking For

A **5/5** answer covers:

- **Retrieval strategy** — semantic, keyword, hybrid — when to use each
- **Re-ranking** — why and how
- **Prompt construction** — how retrieved chunks become LLM input
- **Evidence citation** — forcing the LLM to cite sources
- **Structured output** — Pydantic or similar for reliable parsing
- **Safety** — PII masking, guardrails against hallucination

---

## Core Concepts (Easy Explanation)

### The Basic RAG Flow

```
User query → Retrieve relevant chunks → Build prompt with chunks → LLM generates answer
```

Claim Verifier goes further — it's **Agentic RAG** (the agent decides when and how to search).

### Retrieval Methods

#### 1. Semantic (Vector) Search
- Embed the query, find closest chunk vectors
- **Good for:** Paraphrased questions, conceptual similarity
- **Bad for:** Exact names, dates, IDs, product codes
- **Example:** "When was TikTok banned in India?" matches "India prohibited TikTok on June 29, 2020"

#### 2. Keyword (BM25) Search
- Traditional text matching — counts word overlap
- **Good for:** Exact terms, names, acronyms, IDs
- **Bad for:** Paraphrased or synonym queries
- **Example:** "MeitY TikTok ban 2020" matches documents containing those exact words

#### 3. Hybrid Search
- Combines semantic + keyword scores (weighted sum or reciprocal rank fusion)
- **Best of both worlds** — most production systems use this
- **OpenSearch, Weaviate, Elasticsearch** support hybrid natively
- **Claim Verifier:** Uses semantic-only in ChromaDB, but compensates with Tavily web search for fresh keyword matches

**When to use what:**

| Scenario | Best Method |
|----------|-------------|
| "Explain how RAG works" | Semantic |
| "ISO 27001 certification requirements" | Keyword (exact term) |
| "Latest ODI cricket rankings" | Hybrid + recency filter |
| General fact-checking | Hybrid (ideal) or semantic + web search (what we did) |

### Re-ranking

**Problem:** Vector search is fast but imprecise — top results might be "close" in embedding space but not actually answer the question.

**Solution:** Fetch more candidates (e.g., 12), then re-score each for actual relevance to the query, keep top k (e.g., 4).

**Claim Verifier reranking:**
- **Library:** FlashRank (local, free, no API)
- **Model:** ms-marco-MiniLM-L-12-v2 (trained for passage relevance)
- **Flow:** Fetch `min(k×3, 12)` from ChromaDB → rerank → return top k
- **Fallback:** If reranking fails, return original order truncated to k
- **Transparency:** `rerank_score` added to chunk metadata

**Other rerankers to know:** Cohere Rerank API, cross-encoder models (ms-marco), LLM-based reranking

### Agentic RAG (What Makes Claim Verifier Special)

Instead of "retrieve once → generate once," a **ReAct agent** decides:
- Which tool to call (KB search vs web search)
- What query to use
- Whether to search again (if evidence is insufficient or conflicting)
- When to stop (enough evidence gathered)

**Claim Verifier agent flow:**
1. Search knowledge base first
2. Do at least 2 web searches with different queries
3. For current affairs: include year in query, search for latest data
4. If sources conflict: search again to resolve
5. Max 8 iterations

This is **more powerful** than naive RAG because the agent adapts to the claim.

### Prompt Augmentation

**Prompt augmentation** = how you insert retrieved content into the LLM prompt.

**Claim Verifier uses a two-phase approach:**

**Phase 1 — Evidence Gathering (Agent):**
- Agent calls tools, collects KB chunks + web results
- Combines agent summary + raw tool observations into one evidence string
- Appends source credibility guide (Tier 1–4 scoring)

**Phase 2 — Verdict Generation (Structured Prompt):**
- `VERIFICATION_PROMPT` in `rag_engine/prompts.py`
- Inputs: `{claim}` and `{evidence}`
- Strict rules: no fabrication, cite only provided evidence, prefer most recent source, handle conflicts
- Fixed output format: VERDICT, CONFIDENCE, REASONING, CITATIONS, EVIDENCE QUALITY

### Source Credibility (Claim Verifier's Secret Weapon)

Before the verdict LLM call, URLs are scored:

| Tier | Score | Examples |
|------|-------|----------|
| 1 — Authoritative | 1.0 | WHO, NASA, Reuters, ICC |
| 2 — Reliable | 0.75 | BBC, NYT, Snopes, Wikipedia |
| 3 — Moderate | 0.5 | CNN, regional news |
| 4 — Low Trust | 0.25 | Blogs, forums, unknown |

This is appended as "SOURCE CREDIBILITY GUIDE" so the LLM weights WHO over a random blog.

### Preventing Hallucination (Guardrails)

**Claim Verifier guardrails:**
1. **Prompt rules:** "NEVER fabricate sources", "use ONLY provided evidence"
2. **Structured output format** — parser extracts fixed fields
3. **Source credibility weighting** — prefer authoritative sources
4. **"NOT ENOUGH EVIDENCE"** as valid verdict — LLM doesn't have to guess
5. **Two-phase separation** — agent gathers, separate LLM call verifies (reduces fabrication)

**Production guardrails to mention:**
- PII masking before prompt injection
- Output validation with Pydantic schemas
- Confidence thresholds — don't answer if retrieval score too low
- Citation verification — check URLs actually appeared in retrieved chunks

### Structured Output

**Claim Verifier:** Regex-based parser in `utils/output_parser.py` extracts:
- verdict, confidence, reasoning, citations (source, url, snippet), evidence_quality

**Production approach:** Pydantic models validate LLM output — if parsing fails, retry or return error. Mention this even though Claim Verifier uses regex.

---

## How Claim Verifier Does Retrieval + Prompts (Your Talking Points)

### Retrieval Path (KB)
```
Query → ChromaDB similarity_search (fetch 12) → FlashRank rerank → Top 4 chunks → Formatted for agent
```

### Retrieval Path (Web)
```
Query → Tavily API (advanced depth, 5 results, AI summary) → Formatted for agent
```

### Full Verification Flow
```
1. ReAct Agent gathers evidence (KB + web tools)
2. Combine agent output + raw observations
3. Extract URLs → build credibility context
4. GPT-4o + VERIFICATION_PROMPT → structured verdict
5. Parse response → JSON-like dict
6. Optional: harvest web results back to KB
```

---

## What You'd Improve (Shows Production Thinking)

> "We use semantic search with reranking, plus live web search for freshness. For production, I'd add hybrid search (BM25 + vector) in OpenSearch for better exact-match retrieval on names and dates. I'd replace regex parsing with Pydantic-validated structured output, add PII masking before prompt injection, and implement a similarity threshold below which we skip answering and return 'insufficient evidence.'"

---

## Hands-On Preparation

1. **Trace one claim end-to-end** — pick "India banned TikTok in 2020" and explain every step from query to verdict
2. **Understand why reranking matters** — explain without reranking vs with reranking using a concrete example
3. **Read `rag_engine/prompts.py`** — memorize the 8 strict rules in VERIFICATION_PROMPT
4. **Practice explaining hybrid search** — even though you don't use it, explain WHEN you'd add it
5. **Practice the conflict handling story** — "If BBC says X and a blog says Y, we prefer the most recent authoritative source"

---

## Likely Interview Questions + How to Answer

**Q: Explain your retrieval strategy.**
> A: We use a two-source retrieval strategy. For pre-loaded knowledge, we do semantic search in ChromaDB — embed the query, fetch 12 candidates, rerank with FlashRank ms-marco model to get the top 4 most relevant chunks. For current affairs, our ReAct agent calls Tavily for live web search with advanced depth. The agent decides which source to query and with what search terms, doing at least 3 searches total. This hybrid approach — static KB for established facts, live web for current events — gives us both speed and freshness.

**Q: Why do you rerank? Isn't vector search enough?**
> A: Vector search finds chunks that are semantically close, but close doesn't always mean relevant. For example, a chunk about "TikTok's popularity in India" might rank high for "India banned TikTok" even though it doesn't mention the ban. Reranking with ms-marco scores each candidate for actual relevance to the specific query. We fetch 3x more candidates than needed, rerank, and keep the top k. This significantly improves precision.

**Q: How do you construct the prompt for the LLM?**
> A: We use a two-phase approach. Phase 1: the ReAct agent gathers evidence using KB and web tools, producing raw search results. We combine the agent's summary with raw tool observations, then append a source credibility guide that tiers each URL from Authoritative to Low Trust. Phase 2: all of this goes into VERIFICATION_PROMPT with the original claim. The prompt has strict rules — no fabrication, cite only provided evidence, prefer most recent sources, handle conflicts — and requires structured output: VERDICT, CONFIDENCE, REASONING, CITATIONS, EVIDENCE QUALITY.

**Q: How do you prevent the LLM from hallucinating citations?**
> A: Three layers: First, the prompt explicitly says NEVER fabricate sources and use ONLY provided evidence. Second, evidence comes from tool outputs (KB chunks and Tavily results) with real URLs — the LLM can't invent what it wasn't given. Third, we parse the output with strict regex and validate verdict categories. We also allow "NOT ENOUGH EVIDENCE" as a valid answer so the model doesn't guess when data is insufficient.

**Q: What is agentic RAG and why did you use it?**
> A: Traditional RAG retrieves once and generates once. Agentic RAG gives an LLM agent tools — our agent has search_knowledge_base and search_web — and it decides what to search, how many times, and when it has enough evidence. This is crucial for fact-checking because claims vary wildly — a historical fact needs KB search, while "who is #1 in ODI today" needs live web search with the current year. The agent adapts its strategy per claim.

---

# CRITERION 4: Exposing the RAG System via API or Chatbot (Target: 5/5)

## What Evaluators Are Looking For

A **5/5** answer covers:

- **How users interact** with the system (UI, API, chatbot)
- **Deployment architecture** (cloud, containers, scaling)
- **Session management** and conversation history
- **Authentication and access control**
- **Guardrails** for LLM responses
- **API design** — endpoints, request/response format

---

## Core Concepts (Easy Explanation)

### Ways to Expose a RAG System

| Method | Pros | Cons |
|--------|------|------|
| **Web UI (Streamlit/Gradio)** | Fast to build, great for demos | Not production-grade UX |
| **REST API (FastAPI/Flask)** | Flexible, any client can consume | Need to build frontend separately |
| **Chatbot (Slack/Teams/Discord)** | Meets users where they are | Platform-specific integration |
| **Browser Extension** | Contextual — act on selected text | Limited UI space |
| **Embedded widget** | Add to existing website | iframe/security considerations |

**Claim Verifier uses:** Streamlit web app + Chrome extension (deep-link, not direct API).

### Deployment Architecture

**Claim Verifier deployment:**
- **Docker container** (Python 3.11-slim)
- **docker-entrypoint.sh** — auto-builds static KB if empty, then starts Streamlit on port 8501
- **Deployed on AWS EC2** (IP: 65.0.149.214:8501) for the extension default URL
- **ChromaDB** persisted inside container (no external volume by default)

**Production architecture to discuss:**

```
User → CloudFront/CDN → Load Balancer → Kubernetes pods
                                              ├── API server
                                              ├── Streamlit UI
                                              └── Background workers (ingestion)
         ↓
    S3 (document storage)
    OpenSearch/Pinecone (vector DB)
    Cognito (authentication)
```

### Session Management

**What it means:** Tracking user state across interactions.

**Claim Verifier:**
- `st.session_state` in Streamlit — preserves claim text across page rerenders
- URL query param `?claim=...` — pre-fills claim from extension or shared links
- **No multi-turn conversation** — each verification is independent (stateless backend)

**Production session management:**
- Session ID in JWT or cookie
- Store conversation history in Redis/DynamoDB
- Pass last N messages as context to the agent
- User role determines access (admin vs viewer)

### Authentication and Access Control

**Claim Verifier:** No auth — open hackathon demo.

**Production patterns to know:**

| Method | Use Case |
|--------|----------|
| **API keys** | Service-to-service, simple |
| **JWT tokens** | Stateless user auth, microservices |
| **OAuth 2.0 / Cognito** | User login with Google/email |
| **Role-based access (RBAC)** | Admin can upload docs, viewer can only query |

**How to discuss:** "Our MVP is open access for the hackathon. For production, I'd add AWS Cognito for user authentication, JWT tokens for API calls, and role-based access — admins can manage the knowledge base, users can only verify claims."

### Guardrails for LLM Responses

**Claim Verifier guardrails:**
1. Structured output format (verdict categories enforced)
2. "NOT ENOUGH EVIDENCE" prevents forced answers
3. Source credibility tiers guide LLM weighting
4. UI disclaimer: "AI-powered, may make mistakes"
5. Downloadable result for audit trail
6. Agent max iterations (8) prevents runaway loops
7. Evidence quality rating (STRONG/WEAK/NONE)

**Production guardrails to mention:**
- Rate limiting per user/IP
- Input validation (max claim length, profanity filter)
- Output moderation (block harmful content)
- Logging and audit trail for compliance
- Cost caps per session (limit API calls)

### API Design (Know Even If You Didn't Build One)

A production RAG API might look like:

```
POST /api/v1/verify
  Body: { "claim": "...", "session_id": "..." }
  Response: { "verdict": "TRUE", "confidence": "HIGH", "reasoning": "...", "citations": [...] }

GET /api/v1/kb/stats
  Response: { "total_chunks": 1234, "last_updated": "..." }

POST /api/v1/kb/ingest
  Body: { "url": "...", "category": "..." }
  Auth: Admin only
```

**Claim Verifier equivalent:** The `verify_claim(claim)` function in `rag_engine/agent.py` IS the core API — Streamlit and the extension are just UI layers on top.

---

## How Claim Verifier Exposes the System (Your Talking Points)

### Streamlit Web App (`app.py`)
- **Run:** `streamlit run app.py` on port 8501
- **Features:** Claim input, verify button, verdict display, reasoning, citations, evidence quality, expandable agent steps, downloadable result
- **Session state:** Preserves claim text across rerenders
- **URL pre-fill:** `?claim=encoded_text` from extension
- **Sidebar:** KB stats, how-it-works guide, verdict legend

### Chrome Browser Extension (`extension/`)
- **Manifest V3** extension
- **Context menu:** Right-click selected text → "Verify claim" → opens Streamlit with claim pre-filled
- **Popup:** Manual claim entry → opens app
- **Configurable base URL** in options (default: deployed AWS instance)
- **No direct API calls** — just opens a URL with query param

### Docker Deployment
- `Dockerfile` — Python 3.11-slim, installs deps, copies code
- `docker-entrypoint.sh` — checks if KB is empty → builds static facts → starts Streamlit on 0.0.0.0:8501
- Environment variables: `OPENAI_API_KEY`, `TAVILY_API_KEY`, optional KB harvest settings

### User Flow
```
User types/selects claim → Streamlit UI → verify_claim() → Agent researches → Verdict displayed → Optional download
```

---

## What You'd Improve (Shows Production Thinking)

> "Currently we expose via Streamlit and a Chrome extension that deep-links with query params. For production, I'd wrap verify_claim() in a FastAPI REST API with JWT authentication via Cognito, deploy on Kubernetes with horizontal pod autoscaling, add Redis for session/conversation history, mount persistent volumes for ChromaDB, and put CloudFront in front for caching and HTTPS."

---

## Hands-On Preparation

1. **Run the app locally** — `streamlit run app.py` — verify a claim and observe all UI sections
2. **Test the extension flow** — understand how `?claim=` query param works
3. **Read `docker-entrypoint.sh`** — explain the auto-build logic
4. **Practice drawing the deployment diagram** on paper — User → Extension → Streamlit → Agent → ChromaDB/Tavily/GPT-4o
5. **Prepare a 2-min demo script** — enter claim, show agent steps, show verdict + citations

---

## Likely Interview Questions + How to Answer

**Q: How is your RAG system exposed to users?**
> A: Two entry points. Primary is a Streamlit web app where users type or paste a claim and get a structured verdict with reasoning and citations. Second is a Chrome extension — users select text on any webpage, right-click "Verify claim," and it opens our Streamlit app with the claim pre-filled via URL query parameter. Both ultimately call the same verify_claim() function in our agent module.

**Q: Describe your deployment setup.**
> A: We containerized with Docker on Python 3.11-slim. The entrypoint script checks if the knowledge base is empty and auto-builds static facts, then starts Streamlit on port 8501 bound to 0.0.0.0. We deployed on AWS EC2 for the hackathon demo. ChromaDB persists inside the container. For production, I'd move to Kubernetes with persistent volumes for the vector DB, add a proper REST API layer, and use CloudFront for HTTPS and caching.

**Q: How do you handle session management?**
> A: Each verification is stateless — no multi-turn conversation. Streamlit session state preserves the claim text across page rerenders so it doesn't disappear when the user clicks Verify. The extension passes claims via URL query params. For production with conversation history, I'd add session IDs stored in Redis, passing the last N turns as context to the agent.

**Q: What guardrails do you have?**
> A: Multiple layers. The verification prompt enforces no fabrication and only uses provided evidence. We have a valid "NOT ENOUGH EVIDENCE" verdict so the model doesn't guess. Source credibility tiers guide the LLM to prefer WHO and Reuters over random blogs. Agent iterations are capped at 8. The UI shows a disclaimer that results may contain errors. Agent thinking steps are visible for transparency. For production, I'd add rate limiting, input length validation, and audit logging.

**Q: How would you add authentication?**
> A: Our MVP is open for the hackathon. For production, I'd use AWS Cognito for user registration and login, issue JWT tokens for API authentication, and implement role-based access — admins can manage the knowledge base and ingestion, while regular users can only submit claims for verification.

---

# BONUS: End-to-End Architecture (Draw This From Memory)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LAYER                           │
│   Streamlit Web App (app.py)  +  Chrome Extension           │
└────────────────────────┬────────────────────────────────────┘
                         │ verify_claim(claim)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     AGENT LAYER                              │
│   LangChain ReAct Agent (GPT-4o, max 8 iterations)          │
│   Tools: search_knowledge_base | search_web                  │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌────────────────────────┐
│   KNOWLEDGE BASE      │    │   LIVE WEB SEARCH       │
│   ChromaDB            │    │   Tavily API            │
│   ↓ similarity_search │    │   advanced depth, 5     │
│   ↓ FlashRank rerank  │    │   results + AI summary  │
│   → top 4 chunks      │    │   → formatted results   │
└──────────────────────┘    └────────────────────────┘
           │                              │
           └──────────┬───────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  VERIFICATION LAYER                          │
│   Evidence + Source Credibility Tiers → VERIFICATION_PROMPT  │
│   → GPT-4o → Structured Verdict → Output Parser             │
│   → Optional: Harvest web results back to KB                  │
└─────────────────────────────────────────────────────────────┘
```

---

# BONUS: Quick Reference Cheat Sheet

| Topic | Claim Verifier Choice | Why |
|-------|----------------------|-----|
| Document loading | WebBaseLoader + static facts | Trusted sources, no PDF complexity |
| Chunking | RecursiveCharacterTextSplitter, 300/40 | Small precise chunks for fact-checking |
| Embedding | text-embedding-3-small (1536d) | Fast, cheap, same API key |
| Vector DB | ChromaDB (local, persistent) | Zero infra for MVP |
| Retrieval | Semantic + rerank + live web | Precision + freshness |
| Reranker | FlashRank ms-marco-MiniLM-L-12-v2 | Free, local, passage relevance |
| Agent | ReAct (GPT-4o, 8 max iterations) | Adaptive search strategy |
| Prompt | Two-phase: gather → verify | Separation reduces hallucination |
| Credibility | 4-tier URL scoring | Weight authoritative sources |
| Output | Regex parser → structured dict | Verdict, confidence, citations |
| UI | Streamlit + Chrome extension | Fast demo + contextual access |
| Deploy | Docker on AWS EC2 :8501 | Containerized, portable |

---

# Final Tips for the Interview

1. **Use Claim Verifier as your anchor** — every answer should connect back to what you built
2. **Explain tradeoffs** — "We chose X because Y, but for production I'd switch to Z because..."
3. **Be honest about gaps** — knowing what you DIDN'T build (auth, hybrid search, PII masking) AND why shows maturity
4. **Think aloud about decisions** — chunk size, embedding model, reranking — always give the "why"
5. **15 minutes goes fast** — practice a 2-min project overview, then be ready for deep dives on any criterion
6. **It's a conversation, not a test** — if you don't know something, say "I haven't implemented that yet, but here's how I'd approach it"
7. **Don't memorize definitions** — talk about real problems you solved: "Our chunks were too big and retrieval was imprecise, so we reduced to 300 chars"

Good luck! You built a solid RAG system — now tell the story confidently.
