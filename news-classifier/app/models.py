"""Pydantic models for structured classification output."""

from pydantic import BaseModel, Field
from typing import Literal, Optional


Category = Literal["politics", "sports", "tech", "business"]


class ClassificationResult(BaseModel):
    category: Category = Field(description="News category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    summary: str = Field(description="One sentence summary")
    provider: str = Field(default="openai", description="LLM provider used")
    method: str = Field(default="langchain", description="langchain | raw_sdk | domain_model")


class ClassifyRequest(BaseModel):
    headline: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=100_000)
    user_id: str = Field(default="demo-user")
    tier: Literal["free", "paid"] = Field(default="free")
    use_chain: bool = Field(default=True, description="True=LangChain LCEL, False=raw SDK")


class ClassifyResponse(BaseModel):
    result: ClassificationResult
    tokens_used: Optional[int] = None
    article_compacted: bool = False
    chunks_used: int = 1
    rate_limit_remaining: Optional[int] = None
