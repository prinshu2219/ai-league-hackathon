"""
rag_engine/agent.py
--------------------
The core of the system — the LangChain ReAct Agent.
"""

import os
import re
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from dotenv import load_dotenv

from rag_engine.tools import get_agent_tools
from rag_engine.prompts import VERIFICATION_PROMPT, AGENT_SYSTEM_PROMPT
from utils.output_parser import parse_verdict_response
from utils.source_credibility import build_credibility_context

load_dotenv()


def get_llm() -> ChatOpenAI:
    """Returns GPT-4o with temperature=0 for consistent fact-checking."""
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )


def build_agent() -> AgentExecutor:
    """Builds and returns the LangChain ReAct Agent with tools."""
    llm = get_llm()
    tools = get_agent_tools()
    react_prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=8,
        handle_parsing_errors=True,
        return_intermediate_steps=True
    )

    return agent_executor


def verify_claim(claim: str) -> dict:
    """
    Main function — takes a claim and returns a full verification result.

    Args:
        claim: The claim text to verify

    Returns:
        Structured verdict dict with verdict, confidence, reasoning,
        citations, evidence_quality, and agent_steps.
    """

    print(f"\n{'='*60}")
    print(f"VERIFYING CLAIM: {claim}")
    print(f"{'='*60}\n")

    # ── Step 1: Agent gathers evidence ──────────────────────────────
    agent = build_agent()

    agent_query = (
        f'Please verify the following claim by searching available sources:\n\n'
        f'CLAIM: "{claim}"\n\n'
        f'MANDATORY INSTRUCTIONS:\n'
        f'1. FIRST search the knowledge base\n'
        f'2. THEN do at least 2 separate web searches with different queries\n'
        f'3. If claim involves rankings, scores, stats, or anything "current":\n'
        f'   - Search for LATEST data (include year 2025 or 2026 in query)\n'
        f'   - Search again with a more specific query if result is unclear\n'
        f'4. If sources CONFLICT: search one more time to resolve it\n'
        f'5. Note the DATE of every source you find\n'
        f'6. Only stop when you have evidence from 3+ different sources\n\n'
        f'Minimum searches required: 3'
    )

    try:
        agent_response = agent.invoke({"input": agent_query})
        evidence_summary = agent_response.get("output", "")
        intermediate_steps = agent_response.get("intermediate_steps", [])
    except Exception as e:
        print(f"Agent error: {e}")
        evidence_summary = "Agent encountered an error during search."
        intermediate_steps = []

    # ── Step 1b: Combine agent summary + raw observations ────────────
    raw_observations = []
    for step in intermediate_steps:
        if len(step) >= 2:
            action = step[0]
            observation = step[1]
            tool_name = getattr(action, "tool", "unknown")
            tool_input = getattr(action, "tool_input", "")
            raw_observations.append(
                f"[{tool_name} searched: '{tool_input}']\n{observation}"
            )

    full_evidence = ""
    if evidence_summary:
        full_evidence += f"AGENT SUMMARY:\n{evidence_summary}\n\n"
    if raw_observations:
        full_evidence += "RAW SEARCH RESULTS:\n" + "\n---\n".join(raw_observations)
    if not full_evidence:
        full_evidence = "No evidence found."

    print(f"\nEvidence length: {len(full_evidence)} characters")

    # ── Step 2: Inject source credibility context ────────────────────
    # Extract URLs from evidence and score their credibility
    url_pattern = re.compile(r"URL:\s*(https?://[^\s\n\]]+)")
    urls_found = url_pattern.findall(full_evidence)
    cred_citations = [
        {"url": u, "source": u.split("/")[2] if len(u.split("/")) > 2 else u}
        for u in urls_found
    ]
    credibility_context = build_credibility_context(cred_citations)

    full_evidence_final = full_evidence
    if credibility_context:
        full_evidence_final += f"\n\n{credibility_context}"

    # ── Step 3: Generate structured verdict ─────────────────────────
    llm = get_llm()

    verification_prompt_text = VERIFICATION_PROMPT.format(
        claim=claim,
        evidence=full_evidence_final
    )

    try:
        verdict_response = llm.invoke(verification_prompt_text)
        raw_verdict = verdict_response.content
    except Exception as e:
        print(f"Verdict generation error: {e}")
        raw_verdict = (
            "VERDICT: NOT ENOUGH EVIDENCE\n"
            "CONFIDENCE: LOW\n"
            "REASONING: An error occurred during verification.\n"
            "CITATIONS: None\n"
            "EVIDENCE QUALITY: NONE"
        )

    # ── Step 4: Parse and return structured output ───────────────────
    result = parse_verdict_response(raw_verdict, claim)
    result["agent_steps"] = _format_agent_steps(intermediate_steps)

    print(f"\n{'='*60}")
    print(f"VERDICT: {result['verdict']}")
    print(f"{'='*60}\n")

    return result


def _format_agent_steps(intermediate_steps: list) -> list:
    """Formats agent steps for display in Streamlit UI."""
    formatted_steps = []
    for step in intermediate_steps:
        if len(step) >= 2:
            action = step[0]
            observation = step[1]
            obs_str = str(observation)
            formatted_steps.append({
                "tool_used": getattr(action, "tool", "unknown"),
                "query": getattr(action, "tool_input", ""),
                "result_preview": (
                    obs_str[:300] + "..." if len(obs_str) > 300 else obs_str
                )
            })
    return formatted_steps
