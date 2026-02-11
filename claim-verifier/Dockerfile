# Claim Verifier — deployable image
# Build: docker build -t claim-verifier .
# Run:   docker run -p 8501:8501 -e OPENAI_API_KEY=... -e TAVILY_API_KEY=... claim-verifier

FROM python:3.11-slim

WORKDIR /app

# Install Python deps (no build-time API keys needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app.py .
COPY rag_engine/ rag_engine/
COPY utils/ utils/
COPY scripts/ scripts/

# Create data dir for ChromaDB (will be populated at first run if empty)
RUN mkdir -p data/chroma_db

# Build KB at startup if empty (uses env OPENAI_API_KEY)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["/docker-entrypoint.sh"]
