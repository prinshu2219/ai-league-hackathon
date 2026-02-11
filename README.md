# 🔍 AI Claim Verifier
### AI League Hackathon #1 — RAG / Agentic RAG

A Real-Time News Claim Verification System powered by **GPT-4o**, **LangChain**, and **ChromaDB**.

---

## 🏗️ Architecture

### Verification flow (runtime)

```mermaid
flowchart TB
    subgraph Input["Entry points"]
        A[Streamlit Web App]
        B[Browser Extension]
    end

    subgraph Core["Claim verification pipeline"]
        C[Claim text]
        D[LangChain ReAct Agent]
        E[Evidence + credibility context]
        F[GPT-4o]
        G[Output parser]
    end

    subgraph Tools["Agent tools"]
        T1[search_knowledge_base]
        T2[search_web]
    end

    subgraph KB["Knowledge base path"]
        K1[Query]
        K2[ChromaDB similarity_search]
        K3[Reranker FlashRank]
        K4[Top-k chunks]
    end

    subgraph Web["Live web path"]
        W1[Query]
        W2[Tavily API]
        W3[Search results]
    end

    subgraph Output["Structured result"]
        O1[Verdict]
        O2[Reasoning]
        O3[Citations]
        O4[Agent steps]
    end

    A --> C
    B --> C
    C --> D
    D --> T1
    D --> T2
    T1 --> K1
    K1 --> K2
    K2 --> K3
    K3 --> K4
    K4 --> E
    T2 --> W1
    W1 --> W2
    W2 --> W3
    W3 --> E
    E --> F
    F --> G
    G --> O1
    G --> O2
    G --> O3
    G --> O4
    O1 --> A
    O2 --> A
    O3 --> A
    O4 --> A
```

### RAG components detail

```mermaid
flowchart LR
    subgraph Build["Knowledge base (build time)"]
        direction TB
        S1[Trusted sources]
        S2[Static facts]
        S3[RecursiveCharacterTextSplitter]
        S4[text-embedding-3-small]
        S5[ChromaDB]
        S1 --> S3
        S2 --> S3
        S3 --> S4
        S4 --> S5
    end

    subgraph Retrieve["Retrieve (query time)"]
        direction TB
        R1[Claim / query]
        R2[ChromaDB fetch 3×k]
        R3[Rerank ms-marco]
        R4[Top-k docs]
        R1 --> R2
        R2 --> R3
        R3 --> R4
    end

    subgraph Verify["Verify"]
        direction TB
        V1[Evidence + source credibility]
        V2[GPT-4o]
        V3[Verdict + citations]
        V1 --> V2
        V2 --> V3
    end

    Build -.-> Retrieve
    Retrieve --> Verify
```

### Agentic loop (ReAct)

```mermaid
sequenceDiagram
    participant U as User
    participant A as ReAct Agent
    participant KB as search_knowledge_base
    participant Web as search_web
    participant LLM as GPT-4o

    U->>A: Claim to verify
    loop Until enough evidence or max iterations
        A->>LLM: Thought + available tools
        LLM->>A: Action (tool + query)
        alt Tool: search_knowledge_base
            A->>KB: query
            KB->>A: Formatted KB results
        else Tool: search_web
            A->>Web: query
            Web->>A: Tavily results
        end
        A->>LLM: Observation
    end
    A->>LLM: Evidence summary + claim + credibility
    LLM->>A: VERDICT, REASONING, CITATIONS
    A->>U: Structured result
```

---

## 🛠️ Tech Stack

| Component | Tool |
|-----------|------|
| Frontend | Streamlit |
| LLM | GPT-4o |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB |
| Web Search | Tavily API |
| Framework | LangChain |

---

## 🚀 Setup Instructions

### 1. Clone & Navigate
```bash
cd ai-league-hackathon/claim-verifier
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and fill in your keys:
# OPENAI_API_KEY=sk-****
# TAVILY_API_KEY=tvly-****
```

Get your keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://tavily.com (free tier)

**Optional — grow KB from web results:** After each verification, you can add some of the web search results into the knowledge base so it grows over time. In `.env` set `ENABLE_KB_UPDATE_FROM_WEB=true`. You can also set `KB_UPDATE_MAX_DOCS_PER_RUN=3` (max documents added per run) and `KB_UPDATE_ONLY_WHEN_VERDICT_NOT_UNKNOWN=true` (only add when the verdict is not "NOT ENOUGH EVIDENCE"). Duplicate URLs are skipped.

### 5. Build the Knowledge Base (Run Once)
```bash
# Full build (scrapes web + loads static facts)
python scripts/build_knowledge_base.py

# Fast build (static facts only, good for testing)
python scripts/build_knowledge_base.py --no-web
```

### 6. Run the App
```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

### 7. Deploy (optional)

To run the app on a public URL (for the browser extension or sharing):

- **Streamlit Community Cloud** — Connect your GitHub repo, set root to `claim-verifier`, add secrets, deploy. Free.
- **Docker** — From `claim-verifier/`: `docker build -t claim-verifier .` then `docker run -p 8501:8501 -e OPENAI_API_KEY=... -e TAVILY_API_KEY=... claim-verifier`. Persist the KB with `-v claim-verifier-data:/app/data`.
- **Railway / Render / Fly.io** — Deploy the Dockerfile; set env vars and use the generated URL in the extension.

See **[claim-verifier/DEPLOYMENT.md](claim-verifier/DEPLOYMENT.md)** for step-by-step instructions.

---

## 📁 Project Structure

```
claim-verifier/
├── app.py                          # Streamlit UI
├── requirements.txt                # Dependencies
├── .env.example                    # API keys template
├── .gitignore
│
├── rag_engine/
│   ├── agent.py                    # LangChain ReAct Agent
│   ├── tools.py                    # KB Search + Web Search tools
│   ├── knowledge_base.py           # ChromaDB operations
│   └── prompts.py                  # Prompt templates
│
├── utils/
│   ├── embeddings.py               # OpenAI embeddings setup
│   ├── chunker.py                  # Text splitting logic
│   └── output_parser.py            # Parses AI verdict output
│
├── data/
│   └── chroma_db/                  # ChromaDB data (auto-created)
│
└── scripts/
    └── build_knowledge_base.py     # Populates ChromaDB
```

---

## 🎯 Verdict Types

| Verdict | Meaning |
|---------|---------|
| ✅ TRUE | Claim is supported by evidence |
| ❌ FALSE | Claim is contradicted by evidence |
| ⚠️ PARTIALLY TRUE | Claim is partially correct |
| 🔍 NOT ENOUGH EVIDENCE | Cannot verify with available sources |

---

## 📦 Deliverables Checklist

- [x] Working demo application (Streamlit)
- [x] Architecture diagram (see above)
- [x] Embedding model: `text-embedding-3-small` (OpenAI)
- [x] Vector DB: ChromaDB (local, persistent)
- [x] Chunking: RecursiveCharacterTextSplitter (500 chars, 50 overlap)
- [x] Knowledge base: Static facts + web-scraped articles
- [x] Verification logic: Agentic RAG with ReAct loop
- [x] Always cites sources
- [x] Never fabricates sources
- [x] Returns "Not Enough Evidence" when appropriate
