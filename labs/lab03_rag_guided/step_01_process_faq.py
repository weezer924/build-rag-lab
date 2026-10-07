"""
Extract Q/A pairs from `labs/data/faq_example.md` using a single OpenAI structured
parsing call and write them to `labs/data/faq_example.jsonl` (multiple JSONL rows).

Each output JSONL line is shaped as:
    {"item": {
        "input": <question>,
        "expected_answer": <answer>,
        "expected_tool": "knowledge_assistant",
        "expected_category": <snake_case_category>
    }}

Usage (from the bundle root):
    python -m labs.lab03_rag_guided.step_01_process_faq

Requirements:
- Set OPENAI_API_KEY in your environment.
- Install dependencies: `pip install -U openai pydantic python-dotenv`.

Security best practice: never commit API keys; use environment variables or a local `.env`
excluded from VCS.

Usage (from the bundle root):
    python -m labs.lab03_rag_guided.step_01_process_faq
    # or
    python labs/lab03_rag_guided/step_01_process_faq.py

"""
# TODO - complete these then rerun the script:
# 1) Add 3–5 new Q/A pairs to `labs/data/faq_example.md` under a new section header.
#   - Keep questions concise and answers factual and complete.
#   - Group related Q/A under a section title so a category can be inferred.
# 2) Ensure section titles can be mapped to a snake_case category (e.g., "Promotions & Discounts" -> "promotions_discounts").
# 3) Rerun this script and confirm the console prints of the first 3 samples reflect your additions.
# 4) Introduce new fields, extend the Pydantic schema below and downstream consumers.

import json
import os
from typing import Any

# Load repo-root `.env` first for OPENAI_API_KEY, then lab-local `.env` for
# step-specific overrides (e.g., VECTOR_STORE_ID). Avoid find_dotenv() here:
# once Step 2 creates labs/lab03_rag_guided/.env, find_dotenv() resolves there
# and can skip repo-root keys on reruns.
from dotenv import load_dotenv

_RAG_DIR = os.path.dirname(os.path.abspath(__file__))
_RAG_ENV_PATH = os.path.join(_RAG_DIR, ".env")
_ROOT_ENV_PATH = os.path.abspath(os.path.join(_RAG_DIR, "..", "..", ".env"))
load_dotenv(_ROOT_ENV_PATH)
load_dotenv(_RAG_ENV_PATH, override=True)

# Pydantic is used to define the structured output schema
try:
    from pydantic import BaseModel
except ImportError:
    raise ImportError("Please install pydantic: pip install pydantic -U")

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Please install the OpenAI Python SDK: pip install openai -U")

# Use the latest model available for best extraction quality
MODEL = "gpt-5-nano"


def _get_paths() -> tuple[str, str]:
    """Compute default absolute input and output paths used by this script.

    Returns:
        Tuple[str, str]: `(input_markdown_path, output_jsonl_path)` pointing to
        `labs/data/faq_example.md` and `labs/data/faq_example.jsonl` respectively.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    in_path = os.path.join(base_dir, "data", "faq_example.md")
    out_path = os.path.join(base_dir, "data", "faq_example.jsonl")
    return in_path, out_path


class FAQItem(BaseModel):
    """Structured representation of a single extracted FAQ entry.

    Fields map to downstream consumers (vector store indexing and evals). If you
    evolve this schema (e.g., adding `source_url`), ensure updates in later steps.
    """

    input: str
    expected_answer: str
    expected_tool: str
    expected_category: str


class FAQItemPayload(BaseModel):
    """Wrapper object to match the JSONL line shape: `{ "item": { ... } }`."""

    item: FAQItem


class FAQItemsPayload(BaseModel):
    """Container holding the list of extracted items under key `faqs`."""

    faqs: list[FAQItemPayload]


def _parse_faq_items_with_pydantic(
    md_content: str,
    model: str = MODEL,
    client: OpenAI | None = None,
    max_output_tokens: int = 16384,
) -> list[dict[str, Any]]:
    """Extract all structured FAQ items from markdown content via structured parsing.

    Uses `OpenAI.responses.parse` with a Pydantic schema to obtain strongly-typed
    results in one call.

    Args:
        md_content: Entire markdown contents of the FAQ source file.
        model: Model name used for extraction (defaults to `MODEL`).
        client: Optional pre-initialized OpenAI client (useful for testing/mocking).
        max_output_tokens: Upper bound for the parser's output tokens.

    Returns:
        list[dict[str, Any]]: Each element is shaped as `{ "item": { ... } }`.

    Raises:
        Exception: Propagates any client or parsing errors with context.
    """
    client = OpenAI()

    # System prompt instructs the model to extract all Q/A pairs and return an object with 'faqs'
    # Task: Update the system message below to match the robust extraction prompt from the README-guided or challenge instructions.
    system_msg = (
        "You are an expert at structured data extraction. "
        "Extract all question/answer pairs from the provided markdown FAQ document. "
        "For each, return an object matching the Pydantic type FAQItemPayload: "
        '{"item": {"input": <question>, "expected_answer": <answer>, "expected_tool": "knowledge_assistant", "expected_category": <snake_case_category>}}. '
        "The expected_answer may be multi-paragraph; preserve line breaks using \\\n characters. "
        "Infer the expected_category from the section or context, and convert it to snake_case. "
        "Return an object of type FAQItemsPayload where 'faqs' is a list of FAQItemPayload objects, one per Q/A pair, in the order they appear."
    )

    user_msg = (
        "Extract all Q/A pairs from the following FAQ document. "
        "Return an object with key 'faqs' whose value is a list of FAQItemPayload objects as described.\n\n"
        f"{md_content}"
    )

    try:
        print(f"Parsing with model: {model}, this can take a while...")
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            text_format=FAQItemsPayload,
            max_output_tokens=max_output_tokens,
        )
    except Exception as error:
        print(f"Error during OpenAI API call: {error}")
        raise

    if response.output_parsed is None:
        raise Exception("No output parsed")
    parsed: FAQItemsPayload = response.output_parsed
    return [item.model_dump() for item in parsed.faqs]


def write_jsonl(items: list[dict[str, Any]], out_path: str) -> int:
    """Write a list of item dicts to a JSONL file.

    Args:
        items: List of dictionaries, each shaped as `{ "item": { ... } }`.
        out_path: Absolute path to the output JSONL file.

    Returns:
        int: The number of lines written.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    lines_written = 0
    with open(out_path, "w", encoding="utf-8") as handle:
        for obj in items:
            handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
            lines_written += 1
    return lines_written


def run():
    """
    Main entry point: Extract all FAQ items from the markdown file and write to JSONL.
    """
    in_path, out_path = _get_paths()
    try:
        with open(in_path, "r", encoding="utf-8") as f:
            md_content = f.read()
    except Exception as e:
        print(f"Failed to read input file {in_path}: {e}")
        return

    try:
        faq_items = _parse_faq_items_with_pydantic(md_content, model=MODEL)
    except Exception as e:
        print(f"Failed to parse structured FAQ items: {e}")
        return

    # Print a preview and write all items to JSONL
    print(f"Extracted {len(faq_items)} FAQ items.")
    for i, item in enumerate(faq_items[:3], 1):
        print(f"Sample {i}: {json.dumps(item, ensure_ascii=False)}")
    num_written = write_jsonl(faq_items, out_path)
    print(f"Wrote {num_written} items to {out_path}")


if __name__ == "__main__":
    run()
