"""
rag_engine/agent.py
--------------------
The core of the system — the LangChain ReAct Agent.

This agent:
1. Receives a claim
2. Decides which tools to use (KB search vs web search)
3. Loops through Thought → Action → Observation
4. Stops when it has enough evidence
5. Generates a structured verdict

Flow:
    claim → agent → [searches KB + Web] → evidence → GPT-4o → verdict
"""

import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from dotenv import load_dotenv

from rag_engine.tools import get_agent_tools
from rag_engine.prompts import VERIFICATION_PROMPT, AGENT_SYSTEM_PROMPT
from utils.output_parser import parse_verdict_response

load_dotenv()


def get_llm() -> ChatOpenAI:
    """
    Returns the GPT-4o model instance.

    temperature=0 means:
    - No randomness in responses
    - Same input always gives same output
    - Critical for fact-checking (we want consistency!)
    """
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )


def build_agent() -> AgentExecutor:
    """
    Builds and returns the LangChain ReAct Agent with tools.

    The agent uses the "hwchase17/react" prompt from LangChain Hub,
    which implements the standard ReAct (Reasoning + Acting) loop.

    Returns:
        AgentExecutor ready to verify claims
    """
    llm = get_llm()
    tools = get_agent_tools()

    # Pull the standard ReAct prompt from LangChain Hub
    # This prompt teaches the agent how to do Thought/Action/Observation
    react_prompt = hub.pull("hwchase17/react")

    # Create the ReAct agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt
    )

    # AgentExecutor runs the agent loop
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,           # Shows Thought/Action/Observation in terminal
        max_iterations=6,       # Max 6 tool calls before stopping
        handle_parsing_errors=True,  # Gracefully handle LLM formatting errors
        return_intermediate_steps=True  # Return all steps for transparency
    )

    return agent_executor


def verify_claim(claim: str) -> dict:
    """
    Main function — takes a claim and returns a full verification result.

    This is the ONLY function the Streamlit app needs to call.

    Args:
        claim: The claim text to verify
               e.g. "India banned TikTok permanently in 2020"

    Returns:
        Structured verdict dict:
        {
            "claim": str,
            "verdict": str,
            "confidence": str,
            "reasoning": str,
            "citations": list,
            "evidence_quality": str,
            "agent_steps": list  (the thinking steps for transparency)
        }

    Example:
        result = verify_claim("NASA faked the moon landing")
        print(result["verdict"])    # FALSE
        print(result["reasoning"])  # "Multiple credible sources..."
    """

    print(f"\n{'='*60}")
    print(f"🔍 VERIFYING CLAIM: {claim}")
    print(f"{'='*60}\n")

    # ── Step 1: Agent gathers evidence ──────────────────────────────
    agent = build_agent()

    agent_query = f"""
    Please verify the following claim by searching available sources:
    
    CLAIM: "{claim}"
    
    Search both the knowledge base and the web.
    Collect all relevant evidence, then summarize what you found.
    """

    try:
        agent_response = agent.invoke({"input": agent_query})
        evidence_summary = agent_response.get("output", "")
        intermediate_steps = agent_response.get("intermediate_steps", [])

    except Exception as e:
        print(f"⚠️ Agent error: {e}")
        evidence_summary = "Agent encountered an error during search."
        intermediate_steps = []

    # ── Step 2: Generate structured verdict using evidence ───────────
    llm = get_llm()

    # Fill the verification prompt with claim + collected evidence
    verification_prompt_text = VERIFICATION_PROMPT.format(
        claim=claim,
        evidence=evidence_summary if evidence_summary else "No evidence found."
    )

    try:
        verdict_response = llm.invoke(verification_prompt_text)
        raw_verdict = verdict_response.content
    except Exception as e:
        print(f"⚠️ Verdict generation error: {e}")
        raw_verdict = "VERDICT: NOT ENOUGH EVIDENCE\nCONFIDENCE: LOW\nREASONING: An error occurred during verification.\nCITATIONS: None\nEVIDENCE QUALITY: NONE"

    # ── Step 3: Parse the structured output ─────────────────────────
    result = parse_verdict_response(raw_verdict, claim)

    # Add agent thinking steps for the "Show Reasoning" feature in UI
    result["agent_steps"] = _format_agent_steps(intermediate_steps)

    print(f"\n{'='*60}")
    print(f"✅ VERDICT: {result['verdict']}")
    print(f"{'='*60}\n")

    return result


def _format_agent_steps(intermediate_steps: list) -> list:
    """
    Formats the agent's intermediate steps into readable format
    for display in the Streamlit UI "Show Reasoning" section.

    Args:
        intermediate_steps: Raw steps from AgentExecutor

    Returns:
        List of dicts with 'thought', 'action', 'observation' keys
    """
    formatted_steps = []

    for step in intermediate_steps:
        if len(step) >= 2:
            action = step[0]
            observation = step[1]

            formatted_steps.append({
                "tool_used": getattr(action, "tool", "unknown"),
                "query": getattr(action, "tool_input", ""),
                "result_preview": str(observation)[:300] + "..."
                                  if len(str(observation)) > 300
                                  else str(observation)
            })

    return formatted_steps
