#!/bin/sh
set -e

# Build knowledge base on first run (static facts only, no web scrape)
# Requires OPENAI_API_KEY in environment
if ! python -c "
from rag_engine.knowledge_base import get_kb_stats
s = get_kb_stats()
exit(0 if s.get('total_chunks', 0) > 0 else 1)
" 2>/dev/null; then
  echo "Knowledge base empty — building from static facts..."
  python scripts/build_knowledge_base.py --no-web
fi

exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
