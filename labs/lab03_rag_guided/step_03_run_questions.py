"""
Run questions from `labs/data/sample_01.jsonl` against your Vector Store using
the Responses API with the File Search tool. Writes an augmented JSONL with
model answers for Step 4 evaluation.

Prerequisites:
- Set OPENAI_API_KEY in your environment.
- Ensure `VECTOR_STORE_ID` is set. If not, run `step_02_create_vector_store.py` first.

Usage (from the bundle root):
    python -m labs.lab03_rag_guided.step_03_run_questions
    # or
    python labs/lab03_rag_guided/step_03_run_questions.py

Environment overrides (optional):
- MODEL: Model name (default: "gpt-5-nano").
- EFFORT: Reasoning effort for Responses (low|medium|high). Default: "medium".
- NUM_QUESTIONS: Number of questions to run from the dataset. Default: 11.
- MAX_NUM_RESULTS: File Search top‑k. Default: 5.
- RAG_DATA_FILE: Path to input JSONL (default: labs/data/sample_01.jsonl).
- RAG_OUTPUT_FILE: Output path for the augmented dataset including model answers
  (default: labs/data/rag_model_answer.jsonl).

Output:
- JSONL mirroring dataset items with an added `model_answer` field, suitable for
  Step 4 in `step_04_eval_results.py`.
"""

# TODO - complete these exercises, then proceed to Step 4:
# 1) Try 2–3 different models.
#    - Rerun by exporting MODEL (e.g., MODEL="gpt-5-mini").
# 2) Tune retrieval:
#    - Update EFFORT (low|medium|high) and MAX_NUM_RESULTS (e.g., 3 → 8) and rerun.
#    - Read the system prompt below and strengthen/refine it (citations, refusal
#      when unsupported, concise bullets, style) and compare outcomes.
# 3) Change coverage:
#    - Set NUM_QUESTIONS (e.g., 3, 11) to control how many dataset items run.
# 4) Inspect outputs:
#    - Confirm `labs/data/rag_model_answer.jsonl` was written and contains
#      `model_answer` alongside the original item fields.
# 5) Review the logs at https://platform.openai.com/logs?api=responses to see the file search results and the model answer.

from __future__ import annotations

import json
import os
import sys
import uuid

from dotenv import load_dotenv

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - imported lazily where required
    OpenAI = None  # type: ignore

_RAG_DIR = os.path.dirname(os.path.abspath(__file__))
_RAG_ENV_PATH = os.path.join(_RAG_DIR, ".env")
_ROOT_ENV_PATH = os.path.abspath(os.path.join(_RAG_DIR, "..", "..", ".env"))

# Load environment variables from repo-root `.env` (OPENAI_API_KEY), then
# lab-local `.env` (VECTOR_STORE_ID persisted by Step 2).
load_dotenv(_ROOT_ENV_PATH)
load_dotenv(_RAG_ENV_PATH, override=True)

# Configurable knobs with environment fallbacks
MODEL = os.getenv("MODEL", "gpt-5-nano")
EFFORT = os.getenv("EFFORT", "medium")
NUM_QUESTIONS = int(os.getenv("NUM_QUESTIONS", "11"))
MAX_NUM_RESULTS = int(os.getenv("MAX_NUM_RESULTS", "5"))

# Vector store
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

# Default questions dataset path, resolved relative to this file
DEFAULT_DATA_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "sample_01.jsonl")
)

DATA_FILE = os.getenv("RAG_DATA_FILE") or DEFAULT_DATA_FILE

# Output path for augmented dataset including model answers (single-model only)
DEFAULT_OUTPUT_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "rag_model_answer.jsonl")
)
OUTPUT_FILE = os.getenv("RAG_OUTPUT_FILE") or DEFAULT_OUTPUT_FILE

if not VECTOR_STORE_ID:
    # Print a clear warning and exit if VECTOR_STORE_ID is not set
    print(
        "ERROR: VECTOR_STORE_ID is not set in your environment.\n"
        "Please run step_02_create_vector_store.py to create a new vector store.\n"
    )
    # Exit the script to prevent accidental runs without a valid vector store
    sys.exit(1)


def load_questions_from_jsonl(file_path: str, limit: int) -> list[str]:
    """Load up to `limit` question strings from a JSONL dataset.

    Input lines should look like: {"item": {"input": "...", ...}}. The
    loader skips blank or malformed lines and collects at most `limit` valid
    questions.

    Args:
        file_path: Absolute or relative path to the JSONL dataset.
        limit: Maximum number of questions to return. Must be positive.

    Returns:
        A list of question strings.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If no valid questions are found.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSONL file not found: {file_path}")

    questions: list[str] = []
    with open(file_path, "r", encoding="utf-8") as file_handle:
        for raw_line in file_handle:
            if len(questions) >= limit:
                break
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines rather than aborting the run
                continue

            # Safely navigate to item.input
            item = payload.get("item") if isinstance(payload, dict) else None
            if isinstance(item, dict):
                candidate = item.get("input")
                if isinstance(candidate, str) and candidate.strip():
                    questions.append(candidate.strip())

    if not questions:
        raise ValueError(
            'No valid questions found in the JSONL file. Ensure lines have {"item": {"input": "..."}}'
        )

    return questions


def ask_question(
    client: OpenAI,
    question: str,
    run_uuid: str,
    model: str,
    effort: str,
    max_num_results: int,
) -> str:
    """Ask a single question using the File Search tool and return the answer.

    The system prompt encourages grounded, concise answers with gentle refusals
    when the knowledge base lacks support. Answers should be professional and
    may include brief inline citations (file names) when clearly helpful.
    """

    system_message = (
        "You are a helpful customer support assistant. Use the provided knowledge "
        "base via file search to ground your answers. If the information is not "
        "present in the retrieved files, say you don't know based on the files. "
        "Prefer concise, well-structured bullets. Keep tone polite, positive, "
        "and professional. Avoid guessing or adding unsupported details."
    )

    response = client.responses.create(
        ...  # placeholder for parameters
    )

    return response.output_text.strip()


def write_model_answers_to_jsonl(
    input_file_path: str,
    qa_pairs: list[tuple[str, str | None]],
    output_file_path: str,
) -> int:
    """Write an augmented JSONL with model answers added to each dataset item.

    The function reads the source JSONL and writes the first N valid items to the
    destination, where N == len(qa_pairs). Each written item is augmented with a
    `model_answer` field.

    Args:
        input_file_path: Path to the source dataset JSONL used for questions.
        qa_pairs: List of tuples `(question_text, model_answer_text)` in the same
            order as the selected items from the input file.
        output_file_path: Destination file for the augmented items JSONL.

    Returns:
        The number of lines written.

    Raises:
        ValueError: If there are fewer valid input items than provided answers.
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    lines_written = 0
    with (
        open(input_file_path, "r", encoding="utf-8") as source_handle,
        open(output_file_path, "w", encoding="utf-8") as dest_handle,
    ):
        for raw_line in source_handle:
            if lines_written >= len(qa_pairs):
                break

            line = raw_line.strip()
            if not line:
                continue

            try:
                payload: dict[str, object] = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines rather than aborting
                continue

            item = payload.get("item") if isinstance(payload, dict) else None
            if not isinstance(item, dict):
                # Skip lines missing the expected structure
                continue

            _question_text, model_answer_text = qa_pairs[lines_written]

            # Augment item with the model answer
            new_item = dict(item)
            new_item["model_answer"] = model_answer_text

            # Write out the new JSON line
            new_payload = {"item": new_item}
            dest_handle.write(json.dumps(new_payload, ensure_ascii=False) + "\n")
            lines_written += 1

    if lines_written < len(qa_pairs):
        raise ValueError(
            "Not enough valid items in the input file to match all answers. "
            f"Needed {len(qa_pairs)}, found {lines_written}."
        )

    return lines_written


def run(questions: list[str]) -> None:
    """Run questions for a single model and write the augmented JSONL output."""
    if OpenAI is None:
        raise ImportError("Please install the OpenAI Python SDK: pip install -U openai")

    client = OpenAI()

    # Generate a UUID for this run
    run_uuid = str(uuid.uuid4())
    print(f"Run UUID: {run_uuid}")

    # Helpful runtime info
    print(f"Model: {MODEL}")
    print(f"Vector Store ID: {VECTOR_STORE_ID}")
    print(f"Max file results: {MAX_NUM_RESULTS}")

    answers: list[tuple[str, str | None]] = []
    for index, q in enumerate(questions, start=1):
        print("\n" + "=" * 80)
        print(f"Q{index}: {q}")
        print("-" * 80)
        try:
            answer = ask_question(
                client=client,
                question=q,
                run_uuid=run_uuid,
                model=MODEL,
                effort=EFFORT,
                max_num_results=MAX_NUM_RESULTS,
            )
            print(f"A{index}: {answer}")
            answers.append((q, answer))
        except Exception as error:
            print(f"Error answering Q{index}: {error}")
            answers.append((q, None))

    try:
        num_written = write_model_answers_to_jsonl(
            DATA_FILE,
            answers,
            OUTPUT_FILE,
        )
        print("\n" + "-" * 80)
        print(
            f"Wrote {num_written} augmented item(s) with model answers to: {OUTPUT_FILE}"
        )
    except Exception as write_error:
        print(f"Error writing augmented JSONL: {write_error}")


if __name__ == "__main__":
    # Load questions directly from the configured dataset file
    try:
        questions_to_run = load_questions_from_jsonl(DATA_FILE, NUM_QUESTIONS)
    except Exception as load_error:
        # Provide actionable feedback and exit with non-zero status on failure
        print(f"Error loading questions: {load_error}")
        sys.exit(1)

    run(questions_to_run)
