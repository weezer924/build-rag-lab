"""
Read `labs/data/faq_example.jsonl` and upsert its lines into an
OpenAI Vector Store for File Search.

Behavior:
- Ensure or create a Vector Store (when `vector_store_id` is not provided).
- For each JSONL line (shape: {"item": {input, expected_answer, expected_tool, expected_category}}),
  render a small `.md` file and attach it to the Vector Store.
- If a file with the same deterministic name already exists, delete it first then re‑upload
  (clean up both the Vector Store attachment and the underlying file object).

Chunking note:
- File Search automatically chunks content during ingestion. Chunk size and overlap matter for
  long documents because they control retrieval granularity and continuity across segments.
- In this lab, each uploaded `.md` file is a short, self‑contained FAQ entry, so default
  chunking is sufficient and no explicit tuning is required.

Requirements:
- OPENAI_API_KEY must be set in the environment (e.g., in your shell or `labs/lab03_rag_guided/.env`).
- openai Python SDK installed: `pip install openai -U`
- python-dotenv installed: `pip install python-dotenv`

Usage (from the bundle root):
    python -m labs.lab03_rag_guided.step_02_create_vector_store
    # or
    python labs/lab03_rag_guided/step_02_create_vector_store.py
"""

# TODO - complete these then rerun the script:
# 1) Read `labs/lab03_rag_guided/README.md` (Indexing & file content) to understand how Step 2 fits the flow.
# 2) Review `_ensure_vector_store` and `_upsert_items_from_jsonl` to confirm how files are attached
#   and re‑uploaded if they already exist.
# 3) Research chunking and overlap in Vector Stores/File Search:
#   - Define what chunking and overlap are and why they matter for long documents.
#   - Explain why chunk tuning is unnecessary for short, single‑QA `.md` files in this exercise.
#   - List 2–3 scenarios where you would tune chunk size/overlap.
# 4) OPTIONAL: Advanced, bring in a large document required to be chunked and see how it works.

import hashlib
import io
import json
import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Please install the OpenAI Python SDK: pip install openai -U")

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    raise ImportError("Please install python-dotenv: pip install python-dotenv")

# Load environment variables labs/lab03_rag_guided/.env if present
# If not present, this file will be created automatically by the run function.
_RAG_DIR = os.path.dirname(os.path.abspath(__file__))
_RAG_ENV_PATH = os.path.join(_RAG_DIR, ".env")
# Explicitly load repo-root `.env` for OPENAI_API_KEY (do not use find_dotenv(),
# which will resolve to the lab-local `.env` once Step 2 creates it).
_ROOT_ENV_PATH = os.path.abspath(os.path.join(_RAG_DIR, "..", "..", ".env"))
load_dotenv(_ROOT_ENV_PATH)
# Then load lab-local `.env` for VECTOR_STORE_ID and overrides.
load_dotenv(_RAG_ENV_PATH, override=True)


def _default_jsonl_path() -> str:
    """Return the absolute path to `labs/data/faq_example.jsonl`.

    This mirrors Step 1 output and is used as the default input for indexing.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "data", "faq_example.jsonl")


def _ensure_vector_store(
    client: OpenAI, vector_store_id: str | None, name: str | None
) -> str:
    """
    Resolve and return a usable Vector Store id, creating a new one if needed.

    Resolution order:
    1) If `VECTOR_STORE_ID` exists in the current environment (including `labs/lab03_rag_guided/.env`), use it.
    2) Else if `vector_store_id` function argument is provided, use it.
    3) Otherwise, create a new Vector Store and persist its id to `labs/lab03_rag_guided/.env`.

    Args:
        client: Pre‑initialized OpenAI client.
        vector_store_id: Optional id of an existing Vector Store to reuse.
        name: Optional name to assign when creating a new Vector Store.

    Returns:
        str: A Vector Store id guaranteed to exist.
    """
    # Check for VECTOR_STORE_ID in environment variables
    env_vector_store_id = os.getenv("VECTOR_STORE_ID")
    if env_vector_store_id:
        print(f"Using VECTOR_STORE_ID from environment/.env: {env_vector_store_id}")
        return env_vector_store_id

    # If not found, use the provided argument
    if vector_store_id:
        print(f"Using provided vector_store_id: {vector_store_id}")
        return vector_store_id

    # create a new vector store
    store_name = (
        name or f"faq-example-store-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    )
    vs = client.vector_stores.create(name=store_name)
    print(f"Created vector store: {vs.id} ({store_name})")

    # Write the new vector store id to labs/lab03_rag_guided/.env for future runs
    try:
        if not os.path.exists(_RAG_ENV_PATH):
            with open(_RAG_ENV_PATH, "w", encoding="utf-8") as f:
                f.write(f"VECTOR_STORE_ID={vs.id}\n")
            print(f"Created {_RAG_ENV_PATH} and set VECTOR_STORE_ID={vs.id}")
        else:
            set_key(_RAG_ENV_PATH, "VECTOR_STORE_ID", vs.id)
            print(f"Updated {_RAG_ENV_PATH} with VECTOR_STORE_ID={vs.id}")
        # Ensure current process also has the id available
        os.environ["VECTOR_STORE_ID"] = vs.id
    except Exception as write_error:
        print(
            f"Warning: failed to write VECTOR_STORE_ID to {_RAG_ENV_PATH}: {write_error}"
        )

    return vs.id


def _list_vector_store_files_by_filename(
    client: OpenAI, vector_store_id: str
) -> dict[str, str]:
    """List files attached to a Vector Store and map `filename -> file_id`.

    Paginates through attachments, retrieves each file object to read its canonical filename,
    and returns a dictionary useful for idempotent upserts (detecting and replacing existing files).
    """
    filename_to_file_id: dict[str, str] = {}
    after = None
    while True:
        try:
            page = client.vector_stores.files.list(
                vector_store_id=vector_store_id, limit=100, after=after
            )
        except Exception as error:
            print(f"Could not list vector store files: {error}")
            break

        data = getattr(page, "data", []) or []
        if not data:
            break

        for item in data:
            file_id = getattr(item, "id", None) or getattr(item, "file_id", None)
            if not file_id:
                continue
            try:
                file_obj = client.files.retrieve(file_id)
                filename = getattr(file_obj, "filename", None) or getattr(
                    file_obj, "name", None
                )
                if filename:
                    filename_to_file_id[filename] = file_id
            except Exception as warn:
                print(f"Warning: could not retrieve file {file_id}: {warn}")

        if not getattr(page, "has_more", False):
            break
        try:
            after = getattr(data[-1], "id", None) or getattr(data[-1], "file_id", None)
        except Exception:
            after = None
        if not after:
            break

    return filename_to_file_id


def _slugify(text: str, max_len: int = 80) -> str:
    """Generate a safe, readable slug from input text for filenames.

    Keeps lowercase alphanumerics and underscores/dashes; collapses whitespace and punctuation.
    Truncates to `max_len` characters to avoid overly long filenames.
    """
    text = text.strip().lower()
    # Replace non-alphanumeric with spaces, then collapse to dashes
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "item"


def _item_filename(question: str) -> str:
    """Create a deterministic filename for a FAQ item from its question text.

    Combines a slugified prefix with a short SHA‑1 digest so renames are stable
    unless the question text changes.
    """
    slug = _slugify(question, max_len=60)
    digest = hashlib.sha1(question.encode("utf-8")).hexdigest()[:10]
    return f"faq_{slug}_{digest}.md"


def _iter_jsonl_items(jsonl_path: str) -> Iterable[dict[str, Any]]:
    """Yield parsed JSON objects for each non‑empty line in a JSONL file.

    Lines that fail to parse are skipped with a console warning to avoid aborting the run.
    """
    with open(jsonl_path, "r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as error:
                print(f"Skipping invalid JSONL line: {error}")


def _build_markdown_content(item: dict[str, Any], source_filename: str) -> str:
    """Render a single FAQ item into concise markdown for File Search indexing.

    The content is intentionally short and self‑contained (one Q/A per file). This keeps
    default chunking behavior sufficient for the exercise—no custom chunk size/overlap needed.
    """
    payload = item.get("item", {}) if isinstance(item, dict) else {}
    question = str(payload.get("input", "")).strip()
    answer = str(payload.get("expected_answer", "")).strip()
    category = str(payload.get("expected_category", "unknown")).strip() or "unknown"
    expected_tool = (
        str(payload.get("expected_tool", "knowledge_assistant")).strip()
        or "knowledge_assistant"
    )

    lines = [
        f"Category: {category}",
        f"Source: {source_filename}",
        f"Expected Tool: {expected_tool}",
        "",
        f"Q: {question}",
        "",
        f"A: {answer}",
        "",
    ]
    return "\n".join(lines)


def _upsert_items_from_jsonl(
    client: OpenAI, vector_store_id: str, jsonl_path: str
) -> int:
    """
    Read items from `jsonl_path` and upsert them into the given Vector Store.

    For each item, delete any existing attachment with the deterministic filename, then upload a new
    `.md` file and attach it with useful attributes for filtering.

    Attributes attached on create:
    - kind: "faq_item"
    - category: snake_case category inferred in Step 1
    - item_key: SHA‑1 of the question (stable id for dedupe)
    - source: original JSONL basename

    Returns:
        int: Count of successfully uploaded items.
    """
    existing_by_name = _list_vector_store_files_by_filename(client, vector_store_id)
    submitted_count = 0
    source_filename = os.path.basename(jsonl_path)

    for obj in _iter_jsonl_items(jsonl_path):
        payload = obj.get("item", {}) if isinstance(obj, dict) else {}
        question = str(payload.get("input", "")).strip()
        if not question:
            # Skip lines without a valid question
            continue

        category = str(payload.get("expected_category", "unknown")).strip() or "unknown"

        filename = _item_filename(question)

        # If exists, remove from vector store and delete the file object
        existing_id = existing_by_name.get(filename)
        if existing_id:
            print(
                f"Deleting existing file '{filename}' (file_id={existing_id}) before upserting..."
            )
            try:
                client.vector_stores.files.delete(
                    vector_store_id=vector_store_id, file_id=existing_id
                )
            except Exception as warn:
                print(
                    f"Warning: failed to detach existing file {filename} from vector store: {warn}"
                )
            try:
                client.files.delete(existing_id)
            except Exception as warn:
                print(
                    f"Warning: failed to delete existing file object {existing_id}: {warn}"
                )
            existing_by_name.pop(filename, None)

        # Prepare content and upload a fresh file
        content = _build_markdown_content(obj, source_filename)
        data = io.BytesIO(content.encode("utf-8"))
        data.name = filename

        try:
            uploaded = client.files.create(file=data, purpose="assistants")
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=uploaded.id,
                attributes={
                    "kind": "faq_item",
                    "category": category,
                    "item_key": hashlib.sha1(question.encode("utf-8")).hexdigest(),
                    "source": source_filename,
                },
            )
            submitted_count += 1
            existing_by_name[filename] = uploaded.id
            print(f"Upserted '{filename}' (file_id={uploaded.id})")
        except Exception as error:
            print(f"Failed to upload/attach '{filename}': {error}")

    return submitted_count


def run(
    jsonl_path: str | None = None,
    vector_store_id: str | None = None,
    store_name: str | None = None,
) -> str | None:
    """
    Ingest `faq_example.jsonl` into an OpenAI Vector Store for File Search.

    Args:
        jsonl_path: Absolute path to the JSONL file. Defaults to `labs/data/faq_example.jsonl`.
        vector_store_id: If provided, reuse this Vector Store; otherwise a new one is created.
        store_name: Optional name for a new Vector Store when `vector_store_id` is not provided.

    Returns:
        Optional[str]: The Vector Store id on success, or None on failure.
    """
    jsonl_path = jsonl_path or _default_jsonl_path()
    if not os.path.isabs(jsonl_path):
        # Resolve relative paths safely relative to repository root structure
        jsonl_path = os.path.abspath(jsonl_path)

    if not os.path.exists(jsonl_path):
        print(f"JSONL not found at {jsonl_path}")
        return None

    try:
        client = OpenAI()
    except Exception as error:
        print(f"Failed to initialize OpenAI client: {error}")
        return None

    try:
        vs_id = _ensure_vector_store(client, vector_store_id, store_name)
        total = _upsert_items_from_jsonl(client, vs_id, jsonl_path)
        print(f"Indexing complete. {total} items upserted. Vector store id: {vs_id}")
        return vs_id
    except Exception as error:
        print(f"Indexing failed: {error}")
        return None


if __name__ == "__main__":
    load_dotenv(_RAG_ENV_PATH, override=True)
    run()
