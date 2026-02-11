# Deploying Claim Verifier

You can run the app locally, deploy to **Streamlit Community Cloud** (free), or run it in **Docker** on any host (Railway, Render, Fly.io, AWS, etc.). The browser extension then points to your deployed app URL.

---

## Prerequisites

- **OPENAI_API_KEY** — required for embeddings and GPT-4o.
- **TAVILY_API_KEY** — required for live web search (get one at [tavily.com](https://tavily.com)).

---

## Option 1: Streamlit Community Cloud (free, no Docker)

Good for demos and hackathon submission. The app runs on Streamlit’s servers; the knowledge base is rebuilt on each deploy (or on first start if you use a custom run command).

### Steps

1. **Push your code to GitHub**  
   Ensure the repo contains the `claim-verifier` app (e.g. `claim-verifier/app.py`, `claim-verifier/requirements.txt`, etc.).

2. **Go to [share.streamlit.io](https://share.streamlit.io)**  
   Sign in with GitHub and click **“New app”**.

3. **Configure the app**
   - **Repository:** `your-username/your-repo`
   - **Branch:** `main` (or your default branch)
   - **Root directory:** `claim-verifier` (so imports like `rag_engine` resolve; if your repo root is already the app, leave this blank)
   - **Main file path:** `app.py`
   - **App URL:** optional subpath if you use one

4. **Secrets**  
   In the app’s **Settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   TAVILY_API_KEY = "tvly-..."
   ```

5. **Deploy**  
   Click **Deploy**. The first run will install dependencies from `claim-verifier/requirements.txt`.  
   **Note:** The knowledge base starts empty. Either:
   - Use the app as-is (it will show a sidebar warning and still work with web search), or
   - In **Settings → Advanced → Run command**, set:
     ```bash
     python scripts/build_knowledge_base.py --no-web && streamlit run app.py --server.port=8501
     ```
     (This assumes **Root directory** is `claim-verifier`.) This builds the static-facts KB once per app restart.

6. **Extension**  
   In the extension options, set **Claim Verifier URL** to your app URL, e.g. `https://your-app.streamlit.app`.

---

## Option 2: Docker (run anywhere)

The image builds the knowledge base from static facts on **first container start** (no web scraping), then runs Streamlit. Use a volume if you want the KB to persist across restarts.

### Build and run locally

From the **claim-verifier** directory (where `Dockerfile` lives):

```bash
# Build
docker build -t claim-verifier .

# Run (replace with your keys)
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  -e TAVILY_API_KEY=tvly-... \
  claim-verifier
```

Open **http://localhost:8501**.

### Persist the knowledge base

To keep ChromaDB data across container restarts, mount a volume:

```bash
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  -e TAVILY_API_KEY=tvly-... \
  -v claim-verifier-data:/app/data \
  claim-verifier
```

### Optional env vars

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for LLM and embeddings |
| `TAVILY_API_KEY` | Required for web search |
| `ENABLE_KB_UPDATE_FROM_WEB` | `true` to add web results to KB after verification |
| `KB_UPDATE_MAX_DOCS_PER_RUN` | Max docs to add per run (default `3`) |
| `KB_UPDATE_ONLY_WHEN_VERDICT_NOT_UNKNOWN` | Only grow KB when verdict ≠ NOT ENOUGH EVIDENCE (default `true`) |

---

## Option 3: Deploy Docker to a cloud host

Use the same image and env vars; only the way you run the container changes.

### Railway

1. Create a new project and choose **Deploy from GitHub** (or use **Dockerfile**).
2. Set **Root Directory** to `claim-verifier` if the Dockerfile is inside that folder.
3. Add **Variables:** `OPENAI_API_KEY`, `TAVILY_API_KEY`.
4. Railway will build from the Dockerfile and expose a public URL. Use that URL in the extension.

### Render

1. **New → Web Service**, connect the repo.
2. **Environment:** Docker.
3. **Dockerfile path:** `claim-verifier/Dockerfile` (if repo root is above `claim-verifier`).
4. Add **Environment Variables:** `OPENAI_API_KEY`, `TAVILY_API_KEY`.
5. Deploy and use the generated URL in the extension.

### Fly.io

```bash
# From repo root; Dockerfile in claim-verifier/
cd claim-verifier
fly launch
fly secrets set OPENAI_API_KEY=sk-... TAVILY_API_KEY=tvly-...
fly deploy
```

Use `fly status` or the Fly dashboard for the app URL.

### AWS / GCP / Azure

- Build and push the image to ECR, GCR, or ACR.
- Run the container with the same env vars and port **8501**.
- Optionally mount a volume for `/app/data` to persist the KB.

---

## Browser extension after deploy

1. Install the extension (load unpacked from `claim-verifier/extension`).
2. Open the extension **Options** (or “Set Claim Verifier URL” in the popup).
3. Set **Claim Verifier URL** to your deployed app URL, e.g.:
   - Streamlit Cloud: `https://your-app.streamlit.app`
   - Railway/Render/Fly: `https://your-app.up.railway.app` (or the host they give you)

Then “Verify claim” (from selection or popup) will open your deployed app with the claim pre-filled.

---

## Summary

| Method | Best for | KB persistence |
|--------|----------|------------------|
| **Streamlit Community Cloud** | Quick demo, hackathon | Rebuilt per deploy or via run command |
| **Docker** (local or cloud) | Full control, production-style | Use volume for `/app/data` |
| **Railway / Render / Fly.io** | Hosted Docker with minimal setup | Configure volume if offered |

All options require **OPENAI_API_KEY** and **TAVILY_API_KEY** in the environment (or Streamlit Secrets).
