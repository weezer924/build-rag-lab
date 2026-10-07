"""Optional Section
Run an agentic RAG lookup against the Lab 03 FAQ vector store.

The agent decides when to use OpenAI's hosted File Search tool and grounds its
answer in the retrieved FAQ content.

Prerequisites:
- Install the project dependencies (including ``openai-agents``).
- Set ``OPENAI_API_KEY`` in the environment or the repository ``.env`` file.

Usage:
    python -m labs.lab03_rag_guided.step_05_agent_rag \
        "Can I get a student discount?"
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from agents import Agent, FileSearchTool


LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[1]

# Load a repository API key if one exists. The lab-local file is loaded second
# because earlier Lab 03 steps use it for vector-store configuration.
load_dotenv(REPO_ROOT / ".env")
load_dotenv(LAB_DIR / ".env", override=True)

VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "")
MODEL = os.getenv("AGENT_RAG_MODEL", "gpt-5-nano")
MAX_NUM_RESULTS = int(os.getenv("AGENT_RAG_MAX_NUM_RESULTS", "5"))

AGENT_INSTRUCTIONS = """\
You are Acme's FAQ support agent.

Answer customer questions using the FAQ lookup tool.

Success criteria:
- Look up the customer's question before answering.
- Base factual claims only on evidence returned by the lookup.
- Give a direct, concise, and helpful answer.
- If the lookup does not contain enough evidence, say that the answer is not
  available in the FAQ knowledge base. Do not guess.

Stop after the question is answered or the missing evidence is clearly stated.
"""


def build_lookup_tool(
    *,
    vector_store_id: str = VECTOR_STORE_ID,
    max_num_results: int = MAX_NUM_RESULTS,
) -> "FileSearchTool":
    """Create the hosted lookup tool for the configured OpenAI vector store."""

    if not vector_store_id:
        raise ValueError(
            "VECTOR_STORE_ID is not set. Run Task 5 and confirm "
            "labs/lab03_rag_guided/.env contains VECTOR_STORE_ID=vs_..."
        )
    if not vector_store_id.startswith("vs_"):
        raise ValueError("vector_store_id must be a valid OpenAI vector store ID")
    if max_num_results < 1:
        raise ValueError("max_num_results must be at least 1")

    try:
        from agents import FileSearchTool
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI Agents SDK is required. Run `python -m pip install -r requirements.txt` to install "
            "`openai-agents`."
        ) from error

    return FileSearchTool(
        vector_store_ids=[vector_store_id],
        max_num_results=max_num_results,
    )


def build_agent(
    *,
    model: str = MODEL,
    vector_store_id: str = VECTOR_STORE_ID,
    max_num_results: int = MAX_NUM_RESULTS,
) -> "Agent":
    """Build an FAQ agent that can autonomously call the vector-store lookup."""

    try:
        from agents import Agent
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI Agents SDK is required. Run `python -m pip install -r requirements.txt` to install "
            "`openai-agents`."
        ) from error

    return Agent(
        name="Agentic RAG FAQ Assistant",
        instructions=AGENT_INSTRUCTIONS,
        model=model,
        tools=[
            build_lookup_tool(
                vector_store_id=vector_store_id,
                max_num_results=max_num_results,
            )
        ],
    )


async def ask_question(question: str) -> str:
    """Run one agent turn and return its final grounded answer."""

    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export it or add it to the repository "
            ".env file before running this script."
        )

    try:
        from agents import Runner
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI Agents SDK is required. Run `python -m pip install -r requirements.txt` to install "
            "`openai-agents`."
        ) from error

    result = await Runner.run(build_agent(), question, max_turns=4)
    return str(result.final_output).strip()


def parse_args() -> argparse.Namespace:
    """Parse the single customer question accepted by this example."""

    parser = argparse.ArgumentParser(
        description="Answer a question with agentic RAG over the Lab 03 FAQ store."
    )
    parser.add_argument("question", help="Customer question to answer")
    return parser.parse_args()


def main() -> None:
    """Run the command-line example."""

    args = parse_args()
    print(f"Model: {MODEL}")
    print(f"Vector store: {VECTOR_STORE_ID}")
    answer = asyncio.run(ask_question(args.question))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
