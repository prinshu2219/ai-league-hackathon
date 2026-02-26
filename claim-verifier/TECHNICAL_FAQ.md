# Claim Verifier — Technical FAQ (Detailed)

This document answers **why**, **where**, **what**, and **how** for each major part of the system in simple words. Use it for onboarding, documentation, or hackathon submission.

---

## 1. Chunking — Why, Where, What, How

### What is chunking?

**Chunking** means splitting long text (like a full article or a long fact) into smaller pieces called **chunks** before we store them in the database.

Think of it like cutting a long sandwich into smaller bites: each bite is easier to match to a specific question.

### Why we do it

- **One article = many topics.** A single BBC article might talk about elections, economy, and weather. If we store the whole article as one block, the system gets confused about what it’s “about” when we search.
- **Smaller chunks = more precise retrieval.** When you ask “When did India ban TikTok?”, we want the exact sentence that says “June 29, 2020,” not a 5,000-word page.
- **Overlap = no lost context.** If we cut exactly at a sentence, we might cut “India banned TikTok on June 29, 2020” into two chunks. A small **overlap** (reusing a few words at the boundary) keeps the meaning intact.

So we chunk to make search **accurate** and **focused**.

### Where we do it

Chunking happens in **two places**:

1. **When building the knowledge base**  
   File: `rag_engine/knowledge_base.py` → `add_documents_to_kb()`  
   It calls `split_documents(documents)` from `utils/chunker.py`. Every document (from web scraping or static facts) is split into chunks before being added to ChromaDB.

2. **When harvesting web results into the KB** (optional)  
   File: `rag_engine/agent.py` → `_maybe_harvest_web_results_to_kb()`  
   It creates `Document` objects and passes them to `add_documents_to_kb()`, which again uses the same chunker.

So **every** text that goes into the vector database is chunked first.

### How we do it

- **Strategy:** **RecursiveCharacterTextSplitter** (from LangChain), in `utils/chunker.py`.
- **Parameters we use:**
  - **chunk_size = 300** — Maximum 300 characters per chunk.
  - **chunk_overlap = 40** — Each chunk shares 40 characters with the next (so we don’t lose context at the cut).
- **Separators (in order):**  
  `["\n\n", "\n", ". ", " ", ""]`  
  So the splitter first tries to split on paragraph (`\n\n`), then on line (`\n`), then on sentence (`. `), then on space, and finally on any character. That keeps chunks as “natural” as possible (full paragraphs or sentences when it can).
- **Length function:** We count by **characters** (`len`), not words.

**Example:**  
A 800-character paragraph might become 3 chunks of ~300 chars each, with 40 characters overlapping between chunk1–chunk2 and chunk2–chunk3.

---

## 2. Reranking — Why, Where, What, How

### What is reranking?

**Reranking** is a **second pass** after the first search. First we get a list of candidate chunks from the vector database (by similarity). Then we **score each candidate** for how relevant it really is to the specific claim and keep only the best ones.

### Why we do it

- **Vector similarity is fast but imprecise.** ChromaDB returns chunks whose *embeddings* are close to the query. Sometimes “close in numbers” does not mean “answers the claim.” For example, a chunk about “TikTok in India” might be close to “India banned TikTok” even if it doesn’t mention the ban.
- **Reranking fixes that.** We use a model trained to answer: “How relevant is this passage to this question?” So the **top results after reranking** are the ones that actually help verify the claim.

So we rerank to improve **precision**: the agent sees the most on-topic evidence.

### Where we do it

- **File:** `utils/reranker.py` — defines `rerank_documents(query, documents, top_k)`.
- **Used in:** `rag_engine/knowledge_base.py` inside `search_knowledge_base()`.  
  Flow: get more candidates from ChromaDB → call `rerank_documents()` → return only `top_k` reranked chunks.

So reranking happens **only during search**, not when we add documents.

### How we do it

- **Library:** **FlashRank** (Python).
- **Model:** **ms-marco-MiniLM-L-12-v2** — a small model trained for “passage relevance” (how well a passage answers a query).
- **Process:**
  1. We pass the **query** (the claim or search text) and the **list of candidate chunks** (from ChromaDB).
  2. FlashRank returns a **relevance score** for each chunk (higher = more relevant).
  3. We sort by score descending and take the **top_k** chunks (e.g. top 3 or 4).
  4. We attach the score to each chunk’s metadata as `rerank_score` for transparency.

We do **not** use a fixed score threshold; we always take the **top k** by score. If reranking fails (e.g. exception), we fall back to the first `top_k` chunks in the original order.

---

## 3. Embeddings — Why, Where, What, How

### What are embeddings?

**Embeddings** are a way to turn text into a list of numbers (a **vector**). Similar meanings get similar vectors. So “India banned TikTok” and “TikTok was banned in India” end up with close-by numbers, and the database can find them when you search.

### Why we use them

- The vector database (ChromaDB) cannot store raw text for fast similarity search; it needs **vectors**.
- Once every chunk and every query is a vector, we can use **math** (e.g. cosine similarity) to find “closest” chunks to a query. So embeddings are the bridge between language and retrieval.

### Where we use them

- **Definition:** `utils/embeddings.py` — `get_embedding_model()` returns the embedding model.
- **Used when:**
  1. **Adding to the KB:** ChromaDB uses this model to embed each chunk before storing (via LangChain’s `Chroma` + `embedding_function`).
  2. **Searching the KB:** When you call `similarity_search(query, k=...)`, the same model embeds the query and ChromaDB finds the closest stored chunk vectors.

So **every chunk** and **every search query** goes through the same embedding model.

### How we do it

- **Model:** **OpenAI `text-embedding-3-small`**.
- **API:** Same OpenAI API key as for GPT-4o; we use `langchain_openai.OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=...)`.
- **No chunk size limit in our code for the API** — OpenAI handles long text (with its own truncation if needed). Our **chunk_size=300** is for how we split documents before embedding; each chunk is then embedded as one piece.

So: we chunk first (300 chars), then each chunk is turned into one vector by `text-embedding-3-small`.

---

## 4. ChromaDB — What, Why, Where, How

### What is ChromaDB?

**ChromaDB** is a **vector database**. It stores each chunk as a **vector** (list of numbers from the embedding model) plus **metadata** (e.g. source, URL, category). When you give it a query vector, it returns the stored vectors that are “closest” to it (e.g. by cosine similarity).

### Why we use it

- We need to store thousands of chunks and quickly find the ones most related to a claim. ChromaDB is built for exactly that: **similarity search** over vectors.
- It’s **local and persistent** — data is saved on disk in `data/chroma_db`, so we don’t need a separate cloud database for the hackathon.

### Where we use it

- **Path on disk:** `claim-verifier/data/chroma_db` (set in `rag_engine/knowledge_base.py` as `CHROMA_DB_PATH`).
- **Collection name:** `claim_verifier_kb`.
- **Used in:**  
  - `get_vector_store()` — create/load the store.  
  - `add_documents_to_kb()` — add chunked documents (they get embedded and stored).  
  - `search_knowledge_base()` — embed query, get top `fetch_k` by similarity, then rerank to top `k`.  
  - `url_exists_in_kb()` — check if a URL is already in the KB (for deduplication when harvesting web results).

### How it works in our flow

1. **At build time:** Chunks are embedded with `text-embedding-3-small` and stored in ChromaDB (vector + metadata).
2. **At query time:** The search query is embedded with the same model. ChromaDB runs **similarity search** (e.g. cosine similarity by default in LangChain’s Chroma) and returns the top `fetch_k` results (we use `fetch_k = min(k*3, 12)`). We do **not** set a similarity threshold — we always take the top `fetch_k` by distance, then rerank and keep top `k`.

So ChromaDB = **storage + first-stage retrieval**; reranker = **second-stage refinement**.

---

## 5. Confidence Score — How We Measure It, Thresholds

### What is “confidence” in our app?

**Confidence** is the model’s self-reported level of certainty in the verdict (e.g. “I’m highly confident this claim is true” vs “I’m not very sure”). In the UI it appears as **HIGH**, **MEDIUM**, or **LOW**.

### How we “measure” it (important)

We **do not** compute confidence with a formula or a threshold in code. There is **no numeric score** or cutoff.

- The **verification prompt** in `rag_engine/prompts.py` tells GPT-4o to output a line like:  
  `CONFIDENCE: [HIGH / MEDIUM / LOW]`
- GPT-4o decides based on the evidence (e.g. many strong sources → HIGH; conflicting or few sources → MEDIUM or LOW).
- In `utils/output_parser.py` we **parse** that line with a regex:  
  `r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)"`  
  and put it in `result["confidence"]`. If the line is missing, we default to `"LOW"`.

So **confidence is LLM-generated and then parsed** — no threshold, no numeric scale. It’s a label, not a computed metric.

### Summary

- **No threshold:** We don’t map confidence to a number or filter by it.
- **No formula:** Confidence is whatever the model outputs (HIGH/MEDIUM/LOW).
- **Default:** If parsing fails, we use `"LOW"`.

---

## 6. Initial Knowledge Base Setup — How, Why, When

### What is the “initial” knowledge base?

The **initial** KB is the set of chunks we load **once** (or when we choose to rebuild) into ChromaDB before users start verifying claims. It gives the agent a base of trusted, pre-loaded facts and articles.

### Why we have it

- So the agent can find **static or reference information** quickly (e.g. “India banned TikTok in 2020”, “Moon landing 1969”) without calling the web every time.
- So we have a **curated** set of sources (fact-check sites, Wikipedia, BBC, ICC) instead of relying only on live search.

### When we do it

- **When:** You run the script **manually**, typically once after cloning the repo or when you add new sources.  
  Command:  
  `python scripts/build_knowledge_base.py`  
  or, for a faster test run without web scraping:  
  `python scripts/build_knowledge_base.py --no-web`
- **Re-running:** The script **adds** to the existing collection (it doesn’t clear it by default). So you can run it again when you add new URLs or static facts.

### How we do it (step by step)

Script: **`scripts/build_knowledge_base.py`**.

1. **Load static facts**  
   A list `STATIC_FACTS` (in the script) contains short, hand-written sentences (e.g. India TikTok ban, Moon landing, COVID-19, Chandrayaan-3, ICC rankings note). Each is turned into one LangChain `Document` with metadata (source, url, category).

2. **Optionally load from the web**  
   If you don’t use `--no-web`, the script uses **WebBaseLoader** (LangChain) to fetch each URL in `TRUSTED_SOURCES` (Snopes, FactCheck.org, PolitiFact, Wikipedia pages, BBC, ICC rankings pages). Each loaded page becomes one or more `Document`s with metadata (source, url, category).

3. **Chunk everything**  
   All documents (static + web) are passed to `add_documents_to_kb()`, which calls `split_documents()` from `utils/chunker.py` (300 chars, 40 overlap). So long pages become many chunks.

4. **Store in ChromaDB**  
   `add_documents_to_kb()` gets the vector store, embeds each chunk via the OpenAI embedding model, and stores vectors + metadata in ChromaDB under the collection `claim_verifier_kb`.

So: **static facts + optional web scrape → chunk → embed → save to ChromaDB**. That’s the initial KB setup.

---

## 7. Tavily — What, Why, How

### What is Tavily?

**Tavily** is an external **search API** (like Google Search, but made for AI apps). You send a search query and get back a list of results: title, URL, and a short content snippet (and optionally an AI-generated answer summary).

### Why we use it

- Our ChromaDB knowledge base is **static** (or updated only when we run the build script or harvest). For **current** information (e.g. “Who is #1 in ODI batting today?”, “Latest news about X”), we need **live web search**.
- Tavily gives us that: the agent can call **search_web** and get fresh results. So we combine **KB (reference/static)** + **Tavily (live)** for verification.

### How we use it

- **Where:** `rag_engine/tools.py` — function `_search_web_tool(query)`.
- **API:** We use the **Tavily Python client** (`TavilyClient`). You need `TAVILY_API_KEY` in `.env`.
- **Parameters we pass:**
  - `query` — the search string (e.g. “Babar Azam ODI ranking 2025”).
  - `search_depth="advanced"` — deeper search.
  - `max_results=5` — we get up to 5 result items.
  - `include_answer=True` — we also get Tavily’s own short AI summary (we format it as `[Web Summary]`).
  - `include_raw_content=False` — we only use snippets, not full page content.
- **Output format:** We build a string with blocks like `[Web Result 1]\nTitle: ...\nURL: ...\nContent: ...` (and optionally `[Web Summary]\n...`), separated by `\n---\n`. The agent reads this text and uses it as evidence.

So: **Tavily = live web search**; the agent calls it when it needs up-to-date or extra evidence.

---

## 8. Similarity Matching in ChromaDB — How, Thresholds

### How ChromaDB does similarity matching

- When we call `similarity_search(query, k=fetch_k)` (in `rag_engine/knowledge_base.py`), LangChain’s Chroma:
  1. Embeds the **query** with the same embedding function we use for storage (`text-embedding-3-small`).
  2. Compares the query vector to **all** stored chunk vectors using a **distance metric**. ChromaDB often uses **cosine similarity** (or equivalent distance); LangChain’s Chroma default is typically cosine-based “similarity.”
  3. Returns the **top `fetch_k`** vectors that are closest (e.g. highest cosine similarity or smallest distance).

So “similarity matching” = **nearest-neighbor search in vector space**; no keyword matching.

### Do we use a similarity threshold?

**No.** In our code we do **not** set any minimum similarity score or maximum distance threshold. We always:

1. Ask ChromaDB for the top `fetch_k` results (e.g. 12).
2. Pass those to the **reranker** and keep the top `k` (e.g. 4).

So the only “filter” is **rank**: we take the top candidates by similarity, then the top by rerank score. If the best match is still weak, the **LLM** can still say “NOT ENOUGH EVIDENCE” based on the content; we don’t reject results by a similarity number.

---

## 9. How text-embedding-3-small Works (Internals, in Simple Words)

### What the model does

- **Input:** A string of text (e.g. a chunk or a query).
- **Output:** A **vector** — a list of numbers of fixed length (for this model, the dimension is 1536). Each number is a float.

So the model is a function: **text → vector**.

### Why similar texts get similar vectors

- The model is trained so that **semantically similar** texts get **close** vectors (e.g. high cosine similarity or small Euclidean distance). For example:
  - “India banned TikTok” and “TikTok was banned in India” → vectors close together.
  - “India banned TikTok” and “The weather is nice” → vectors far apart.

So the **meaning** is encoded in the position of the vector in space.

### Technical details (simplified)

- It’s a **neural network** (Transformer-based) trained on huge amounts of text. During training, the network learns to place similar meanings in similar directions in the 1536-dimensional space.
- **We don’t train it** — we only call the OpenAI API. We send text; the API returns the vector. We don’t see or set any internal parameters.
- **Length:** Very long texts may be truncated by the API. Our chunks are small (300 chars), so we’re well within limits.

So in short: **text-embedding-3-small** turns text into a 1536-dimensional vector so that “similar meaning ⇒ similar vector,” and we use that for storage and search in ChromaDB.

---

## 10. Other Major Points

### Source credibility

- **What:** We assign each URL a **credibility tier** (1–4) and a label (e.g. Authoritative, Reliable, Moderate, Low Trust) in `utils/source_credibility.py`. Tier 1 = official/wire (e.g. WHO, Reuters, ICC); Tier 4 = unknown/blogs.
- **Why:** So the LLM doesn’t treat a random blog like BBC; we tell it which sources to prefer.
- **How:** After the agent gathers evidence, we extract URLs from the evidence text, look up each URL’s tier in our lists, and append a “SOURCE CREDIBILITY GUIDE” to the evidence before calling the verification prompt. The model sees this and can weight sources accordingly.

### Verification prompt and no fabrication

- The **verification prompt** (`rag_engine/prompts.py`) strictly tells the model to:
  - Use **only** the evidence provided.
  - **Never** invent sources or URLs.
  - Prefer **most recent** source when there’s conflict.
  - Output **VERDICT**, **CONFIDENCE**, **REASONING**, **CITATIONS**, **EVIDENCE QUALITY** in a fixed format so we can parse it in `utils/output_parser.py`.

So **verification logic** = one dedicated LLM call with strict instructions + parsing; no separate “confidence formula” or similarity threshold.

### Optional: growing the KB from web results

- If `ENABLE_KB_UPDATE_FROM_WEB=true` in `.env`, after each verification we may **add** some of the web search results (from Tavily) into ChromaDB so the KB grows over time.
- We only add results from **search_web** tool steps; we parse the observation with `utils/web_result_parser.py`, deduplicate by URL (and skip if URL already in KB), and add up to `KB_UPDATE_MAX_DOCS_PER_RUN` (e.g. 3) new documents. Optionally we only add when the verdict is not “NOT ENOUGH EVIDENCE” (`KB_UPDATE_ONLY_WHEN_VERDICT_NOT_UNKNOWN`).
- New documents are chunked and embedded the same way as in the initial build.

### Agent loop (ReAct)

- The **agent** (GPT-4o + tools) decides **which** tool to call and **with what query**. It must search the KB first, then do at least 2 web searches (and more for current affairs). Max iterations are capped (e.g. 8) so it doesn’t run forever. So **when** we use Tavily is decided by the agent, not by a fixed rule in code.

### Summary table

| Topic            | Where / How |
|------------------|-------------|
| Chunking         | `utils/chunker.py` — RecursiveCharacterTextSplitter, 300 chars, 40 overlap; used in `add_documents_to_kb` and when harvesting. |
| Reranking        | `utils/reranker.py` — FlashRank, ms-marco-MiniLM-L-12-v2; used in `search_knowledge_base` after ChromaDB fetch. |
| Embeddings       | `utils/embeddings.py` — OpenAI text-embedding-3-small; used by ChromaDB for store and query. |
| ChromaDB         | `rag_engine/knowledge_base.py` — persistent store at `data/chroma_db`, collection `claim_verifier_kb`; top-k retrieval, no similarity threshold. |
| Confidence       | LLM output (HIGH/MEDIUM/LOW); parsed in `output_parser.py`; no numeric threshold. |
| Initial KB       | `scripts/build_knowledge_base.py` — static facts + optional web scrape → chunk → embed → ChromaDB. |
| Tavily           | `rag_engine/tools.py` — live web search for the agent; `TAVILY_API_KEY` required. |
| Similarity       | ChromaDB similarity_search returns top `fetch_k`; no threshold; then rerank to top `k`. |
| text-embedding-3-small | Neural model mapping text → 1536-d vector; similar meaning ⇒ similar vector; used via OpenAI API. |

---

*This doc is part of the Claim Verifier project (AI League Hackathon). For setup and architecture, see README.md and DESIGN.md.*
