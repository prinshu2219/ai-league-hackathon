"""
LangChain LCEL chain — prompt | llm | parser

Main classification path for the News Classifier.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

from app.config import config
from app.models import ClassificationResult

logger = logging.getLogger(__name__)

parser = JsonOutputParser(pydantic_object=ClassificationResult)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You classify news articles into politics, sports, tech, or business.\n"
        "{format_instructions}",
    ),
    ("user", "Headline: {headline}\n\nBody: {body}"),
])


def build_chain():
    """Returns the LCEL chain: prompt | llm | parser"""
    llm = ChatOpenAI(
        model=config.PRIMARY_MODEL,
        temperature=0,
        openai_api_key=config.OPENAI_API_KEY,
        request_timeout=config.REQUEST_TIMEOUT,
    )
    return prompt | llm | parser


def classify_with_chain(headline: str, body: str) -> ClassificationResult:
    """
    Run LangChain LCEL chain.
    LangChain text extraction internally uses AIMessage.content.
    """
    chain = build_chain()
    result = chain.invoke({
        "headline": headline,
        "body": body,
        "format_instructions": parser.get_format_instructions(),
    })

    if isinstance(result, dict):
        result["provider"] = "openai"
        result["method"] = "langchain"
        return ClassificationResult(**result)

    result.provider = "openai"
    result.method = "langchain"
    return result
