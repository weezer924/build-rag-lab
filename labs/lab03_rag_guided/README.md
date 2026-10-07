# Builder Bootcamp: Build a RAG pipeline with File Search, Responses, and Promptfoo

### Lab metadata

- **Lab type**: Guided, hands-on
- **Duration**: ~60-75 minutes
- **Level**: Advanced builders
- **Environment**: macOS/Linux/Windows terminal, Node.js 24 LTS, Python 3.12+
- **Bundle path**: `labs/lab03_rag_guided`
- **Last updated:** July 19, 2026

### Overview
In this lab, you will use OpenAI’s File Search and Responses APIs with Promptfoo to build and evaluate a helpdesk-style Retrieval-Augmented Generation (RAG) pipeline. You will:
- **Extract a structured dataset** of Q/A pairs from a markdown FAQ.
- **Create and populate a vector store** with searchable FAQ entries.
- **Ask questions** against the vector store and record model answers.
- **Evaluate alignment** between expected answers and model answers using model-based grading.

This lab is tightly focused to help you quickly master the essentials of structuring data, building retrieval pipelines, and evaluating answer quality in real-world support scenarios, all within the context of a production-style customer support use case—the kind you'd encounter in an actual helpdesk environment.

### Learning objectives
By the end of this lab you will be able to:
1. Structure unstructured FAQs into a consistent, machine‑readable dataset suitable for retrieval and evaluation.
2. Build a reusable vector store and understand how indexing choices impact retrieval quality.
3. Retrieve context and generate grounded answers with configurable model and reasoning settings.
4. Evaluate answer quality with automated graders, interpret pass/total results, and tune thresholds.

### Prerequisites
- **Python**: 3.12+ required
- **Node.js**: 24 LTS recommended
- **Dependencies**: `openai`, `pydantic`, `python-dotenv`
- **Promptfoo**: Run through `node scripts/promptfoo.mjs`; no global installation is required
- **API key**: Environment variable `OPENAI_API_KEY`
- **Access**: Org/project must have access to File Search and Responses
- **Model access**: The API project associated with the key must be able to use the configured OpenAI grader model

## Task 1: Set up your environment

Complete download, extraction, dependency installation, and credential setup in the [bundle root README](../../README.md). Run **every command in this guide from the bundle root**, the directory containing `README.md`, `requirements.txt`, and `labs/`.

## Task 2: Explore the lab files

Let’s take a moment to learn more about the files in this lab directory and get familiar with the datasets that we’ll be leveraging for this exercise.

### What’s in this lab directory

Here’s a quick overview of the main scripts and files you’ll use throughout this lab:

| File | Purpose | Output/Notes |
| --- | --- | --- |
| `step_01_process_faq.py` | Extracts Q/A pairs from `faq_example.md` to a structured dataset. | Writes `labs/data/faq_example.jsonl`. |
| `step_02_create_vector_store.py` | Creates/uses a vector store and uploads each FAQ entry as a small `.md` for File Search. | Saves `VECTOR_STORE_ID` to `labs/lab03_rag_guided/.env`. |
| `step_03_run_questions.py` | Loads questions from `sample_01.jsonl`, queries the vector store via the Responses API, and generates grounded answers. | Writes results (incl. `model_answer`) to `labs/data/rag_model_answer.jsonl`. |
| `step_04_eval_results.py` | Compatibility launcher for the RAG Promptfoo eval. | Runs the pinned config over `rag_model_answer.jsonl`. |
| `promptfooconfig.yaml` | Defines the answer-alignment rubric. | Adjust the normalized threshold or add assertions as needed. |
| `load_tests.py` | Adapts the generated RAG JSONL into Promptfoo test cases. | Preserves the existing `item` fields. |

Explore these files before continuing; note questions to revisit at each checkpoint.

### Preview the data
Before you begin the hands‑on steps, let's review the key data files used in this lab.

1. `labs/data/faq_example.md`: Source markdown FAQ that you will update and parse in tasks 3 and 4.
2. `labs/data/faq_example.jsonl`: Structured dataset written by Task 4.
3. `labs/data/sample_01.jsonl`: Sample customer questions used by Task 6.
4. `labs/data/rag_model_answer.jsonl`: Augmented output with questions and model answers produced in Task 6.

Review the source FAQ and questions now. Both JSONL outputs are intentionally absent until you generate them.

## Task 3: Update the FAQ data

You will now add a new “Sustainability & Ethics” section to the FAQ to broaden coverage and improve dataset completeness.

1. Open the `faq_example.md` file and append the following at the end of the file (keep the visual separator style and numbering):

```markdown

Sustainability & Ethics
	101.	Do you use sustainable packaging?
Yes, our packaging is made from 95% recycled or biodegradable materials.
	102.	Are your products carbon neutral?
Yes, we offset all carbon emissions from manufacturing and shipping.
	103.	How do you ensure ethical sourcing?
We work with certified suppliers who meet international labor and environmental standards.
	104.	Do you support product recycling?
Yes, we offer a take-back program for electronics and apparel recycling at no extra cost.
	105.	Do you donate unsold inventory?
Yes, unsold items are donated to partner charities rather than discarded.

⸻
```

**Checkpoint:** Check that your new section was added correctly with this command:

```bash
sed -n '/^Sustainability & Ethics$/,/^⸻$/p' labs/data/faq_example.md | sed -n '1,20p'
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
Get-Content labs/data/faq_example.md |
  Select-String -Pattern '^Sustainability & Ethics$' -Context 0,20
```
</details>

**Expected output (truncated):**
```text
Sustainability & Ethics
	101.	Do you use sustainable packaging?
Yes, our packaging is made from 95% recycled or biodegradable materials.
	102.	Are your products carbon neutral?
Yes, we offset all carbon emissions from manufacturing and shipping.
...
```

With the dataset updated, you’re ready to continue to the next step.

## Task 4: Extract FAQ to JSONL

Let's extract all Q/A pairs from the FAQ and write them to JSONL (one JSON object per line) for easy streaming and diffing. 

Each object includes `input`, `expected_answer`, `expected_tool`, and `expected_category`, which are used for indexing (Task 5), grounding and answers (Task 6), and evaluation (Task 7).

> **Note:** JSONL’s line‑delimited format is easy to append, jq‑friendly, and scales well to large files.

1. Open `step_01_process_faq.py`, find the `system_msg` variable (around line 113), and replace the placeholder with what's below:

```bash
        "You are an expert at structured data extraction. "
        "Extract all question/answer pairs from the provided markdown FAQ document. "
        "For each, return an object matching the Pydantic type FAQItemPayload: "
        '{"item": {"input": <question>, "expected_answer": <answer>, "expected_tool": "knowledge_assistant", "expected_category": <snake_case_category>}}. '
        "The expected_answer may be multi‑paragraph; preserve line breaks using \\n characters. "
        "Infer the expected_category from the section or context, and convert it to snake_case. "
        "Return an object of type FAQItemsPayload where 'faqs' is a list of FAQItemPayload objects, one per Q/A pair, in the order they appear."
```

This ensures every entry follows a predictable schema, making it easy for downstream scripts to index, retrieve, and evaluate the data reliably, and aligns with the Pydantic types defined in the script.

**Checkpoint:** Run the following command to make sure you updated the system prompt in your script as instructed:

```bash
grep -A 8 'system_msg =' labs/lab03_rag_guided/step_01_process_faq.py
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
Select-String -Path labs/lab03_rag_guided/step_01_process_faq.py -Pattern 'system_msg =' -Context 0,8
```
</details>

**Expected output:**
```bash
    system_msg = (
        "You are an expert at structured data extraction. "
        "Extract all question/answer pairs from the provided markdown FAQ document. "
        "For each, return an object matching the Pydantic type FAQItemPayload: "
        '{"item": {"input": <question>, "expected_answer": <answer>, "expected_tool": "knowledge_assistant", "expected_category": <snake_case_category>}}. '
        "The expected_answer may be multi‑paragraph; preserve line breaks using \\n characters. "
        "Infer the expected_category from the section or context, and convert it to snake_case. "
        "Return an object of type FAQItemsPayload where 'faqs' is a list of FAQItemPayload objects, one per Q/A pair, in the order they appear."
    )
```

2. Now that we've set our system message, let's run the extraction script:

```bash
python -m labs.lab03_rag_guided.step_01_process_faq
```

The script reads `labs/data/faq_example.md` and writes structured entries to `labs/data/faq_example.jsonl` for use in Task 5.

**Checkpoint**: Confirm the JSONL file exists and inspect the first record.

```bash
python -c "import json; print(json.dumps(json.loads(open('labs/data/faq_example.jsonl', encoding='utf-8').readline()), indent=2))"
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
if (Test-Path 'labs/data/faq_example.jsonl') {
    Get-Content 'labs/data/faq_example.jsonl' |
      Select-Object -First 1 |
      ForEach-Object { $_ | ConvertFrom-Json | ConvertTo-Json -Depth 6 }
}
```
</details>

**Expected output:**
```json
{
  "item": {
    "input": "How do I create an account?",
    "expected_answer": "Click “Sign Up,” enter your email, set a password, and verify via email. It takes less than two minutes.",
    "expected_tool": "knowledge_assistant",
    "expected_category": "account_and_login"
  }
```

Behind the scenes, `step_01_process_faq.py` takes the FAQ markdown and sends it to the Responses API, which uses a schema to extract the main fields for each entry: the question (`input`), the answer (`expected_answer`), and the tool (`expected_tool`). 

The LLM also analyzes the context or section headers to infer and assign a category (`expected_category`) to each Q/A pair. The result is a list of structured objects, each conforming to the schema, ready for downstream indexing and evaluation.

**Checkpoint:** Check the extracted FAQ categories and their counts with this command:

```bash
jq -r '.item.expected_category' labs/data/faq_example.jsonl | sort | uniq -c | sort -nr
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
Get-Content 'labs/data/faq_example.jsonl' |
  ForEach-Object { ($_ | ConvertFrom-Json).item.expected_category } |
  Group-Object |
  Sort-Object Count -Descending |
  Format-Table Count, Name -AutoSize
```
</details>

**Expected output (example):**
```text
10 customer_support
   7 orders_and_payments
   7 account_and_login
   6 shipping_and_delivery
   6 miscellaneous
   5 technical_support
   5 sustainability_and_ethics
```

You should see a category like `sustainability_and_ethics` for the latest questions you added to `faq_example.md` as well. This confirms your structured dataset reflects all current topics and is ready to be indexed into a vector store.

With your structured FAQ data ready, let's explore how to make it searchable and useful for downstream applications.

## Task 5: Create & populate a vector store

In this step, you’ll turn each structured FAQ entry into a compact markdown document and upload it using the Responses API’s File Search feature. This creates a reusable vector store and allows the script to save its ID for later retrieval and answering.

1. Open `step_02_create_vector_store.py` and inspect the following functions:

| Function | Purpose | Notes |
| --- | --- | --- |
| `_ensure_vector_store` | Resolve or create a usable vector store ID and persist it to `labs/lab03_rag_guided/.env`. | Checks env, `.env`, and any provided argument; creates if missing. |
| `_list_vector_store_files_by_filename` | Build a `filename -> file_id` map of current attachments. | Enables idempotent replaces to keep uploads up to date and avoid duplicates. |
| `_build_markdown_content` | Render one FAQ item into a concise, self‑contained `.md` with explicit fields. | Short files work well with default File Search chunking; no custom tuning needed. |
| `_upsert_items_from_jsonl` | Stream items, replace existing attachments, and upload fresh `.md` files. | Returns the number of items upserted. |

2. Now that you have an understanding of the file setup and functionality, run the script with the following command:

```bash
python -m labs.lab03_rag_guided.step_02_create_vector_store
```

When you run this script, it reads your structured FAQ JSONL file and processes each entry by rendering it into a compact markdown document. Each markdown file is then uploaded to File Search, with the script ensuring that any previous version of the file (based on a deterministic filename) is replaced—keeping your vector store current and free of duplicates. 

If you haven’t specified a `vector_store_id`, the script will handle creating a new vector store or reusing an existing one, and will save its ID for future use. By the end, your entire FAQ dataset will be indexed and ready for semantic search and retrieval.

> **Note:** File Search automatically chunks content during ingestion. Since each uploaded `.md` is a short, self-contained FAQ, the default settings are sufficient—no chunk tuning is required.

> **If indexing stalls:** Stop with Ctrl+C and inspect the store in the Storage page. Keep its ID until you have finished cleanup. Do not erase the ID and rerun blindly: that creates another persistent store. Only reuse the store created for this bundle.

**Checkpoint**: Confirm you receive a similar output to the following:

```bash
Created vector store: <your-vector-store-id> (faq-example-store-20250922-222249)
Updated <bundle-root>/labs/lab03_rag_guided/.env with VECTOR_STORE_ID=<your-vector-store-id>
Upserted 'faq_how-do-i-create-an-account_835a5474e2.md' (file_id=<your-file-id>)
Upserted 'faq_i-forgot-my-password-how-can-i-reset-it_c1eb73cc87.md' (file_id=<your-file-id>)
Upserted 'faq_can-i-change-my-email-address_d25de7daaf.md' (file_id=<your-file-id>)
..............
Indexing complete. 106 items upserted. Vector store id: <your-vector-store-id>
```

At this point, your documents from `labs/data/faq_example.jsonl` have been uploaded and indexed into a newly created or reused vector store. The unique identifier for this vector store, `VECTOR_STORE_ID=<...>`, has also been written into `labs/lab03_rag_guided/.env` for easy reference in future steps.

**Checkpoint:** Run the following command to verify that your `VECTOR_STORE_ID` has been saved:

```bash
grep VECTOR_STORE_ID labs/lab03_rag_guided/.env
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
Select-String -Path 'labs/lab03_rag_guided/.env' -Pattern 'VECTOR_STORE_ID'
```
</details>

**Expected output:**
```text
VECTOR_STORE_ID=vs_...
```

Next, inspect your vector store in the Platform console to verify the uploads.

3. Open the [Storage page](https://platform.openai.com/storage).

4. In Storage, find your vector store using the ID printed from the last command (`VECTOR_STORE_ID=...`).

The console should list your vector store and many short `.md` files, one per FAQ.

**Indexing checkpoint:** Wait until every attachment reports `completed` and none report `failed` before Task 6. The script submits attachments asynchronously; its “Indexing complete” message alone does not prove readiness. The source screenshot is omitted because it contains a previous vector-store ID.

5. Open the store and verify the attachments show many short `.md` files (e.g., `faq_how-do-i-create-an-account_....md`) with recent timestamps.

> **Troubleshooting:** If you don’t see your files, confirm the org/project is correct and the ID matches, then rerun Task 5.

You've successfully converted each FAQ entry into a markdown document, uploaded the files to File Search, and saved the resulting `VECTOR_STORE_ID` to `labs/lab03_rag_guided/.env`. 

Next, you’ll use this vector store with the Responses API to answer questions by retrieving relevant context from your indexed FAQ files.

## Task 6: Ask questions with File Search and Responses 

In this task, you’ll attach the vector store you created in Task 5 (via `VECTOR_STORE_ID` in `labs/lab03_rag_guided/.env`) and use the Responses API with File Search to answer customer‑style questions. You’ll work in the `step_03_run_questions.py` file.

At a high level, the script attaches your vector store, retrieves relevant context from the uploaded `.md` FAQ files for each question, generates grounded answers, and writes those answers to a new JSONL file for evaluation.

1. Open the `step_03_run_questions.py` file and review the core functions:

    | Function | Purpose |
    | --- | --- |
    | `load_questions_from_jsonl` | Load up to N questions from the dataset; skip malformed lines; error if none found. |
    | `ask_question` | Call Responses with File Search using your vector store, chosen model, reasoning effort, and top‑K results; returns the answer text. |
    | `write_model_answers_to_jsonl` | Write an augmented JSONL mirroring the input items with a new `model_answer` field. |
    | `run` | Orchestrate the flow: print run metadata, loop over questions, gather answers, and write output to disk. |

2. Now absorb the key paramters:

   | Setting | Purpose |
   | --- | --- |
   | `VECTOR_STORE_ID` | Attaches your indexed FAQ files to File Search. |
   | `RAG_DATA_FILE` | Input questions JSONL (e.g., `labs/data/sample_01.jsonl`). |
   | `RAG_OUTPUT_FILE` | Output augmented JSONL with `model_answer`. |
   | `MODEL` | Model used for answering. |
   | `EFFORT` | Reasoning effort: low/medium/high. |
   | `MAX_NUM_RESULTS` | Top‑K retrieved documents. |
 
 3. In `step_03_run_questions.py`, find `ask_question(...)`, and replace the `client.responses.create` placeholder ( around line 171) with the following code:

```python
    response = client.responses.create(
            model=model,
            reasoning={"effort": effort},
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": question},
            ],
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": max_num_results,
            }],
            metadata={"run_uuid": run_uuid},
        )
```

Your Task 5 vector store for file search, model, and reasoning effort are now all set—this ensures your answers are grounded in the uploaded knowledge base.

4.. Now run the script to generate answers for your questions using your uploaded FAQ files as the knowledge base:

```bash
python -m labs.lab03_rag_guided.step_03_run_questions
```

**Checkpoint:** Confirm the run metadata prints and that the correct `VECTOR_STORE_ID` is loaded from `labs/lab03_rag_guided/.env`. You should then see output similar to:

```bash
Run UUID: febfdae8-f890-467e-8266-609cc571fb04
Model: gpt-5-nano
Vector Store ID: <your-vector-store-id>
Max file results: 5

================================================================================
Q1: Can I get a student discount?
--------------------------------------------------------------------------------
A1: - Yes. There is a student discount for verified students. Verified students receive 15% off. 
- The discount requires valid student verification. 

Would you like me to help you start the verification process or provide more details on eligibility?

........

Wrote 11 augmented item(s) with model answers to: <bundle-root>/labs/data/rag_model_answer.jsonl
```

**Checkpoint:** Run the command below to verify the structure of one of the model answers entries.

```bash
sed -n '1p' labs/data/rag_model_answer.jsonl | jq '.item'
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
Get-Content 'labs/data/rag_model_answer.jsonl' -TotalCount 1 |
  ForEach-Object { $_ | ConvertFrom-Json | Select-Object -ExpandProperty item } |
  ConvertTo-Json -Depth 6
```
</details>

**Expected output:**
```json
{
  "input": "Can I get a student discount?",
  "expected_answer": "Yes, verified students receive 15% off.",
  "expected_tool": "knowledge_assistant",
  "expected_category": "promotions_discounts",
  "model_answer": "- Yes. There is a student discount for verified students. Verified students receive 15% off. \n- The discount requires valid student verification. \n\nWould you like me to help you start the verification process or provide more details on eligibility?"
}
```

This is where it all comes together: you can now see the original question (`input`), the reference answer you’ll use for grading (`expected_answer`), routing signals (`expected_tool`, `expected_category`), and the grounded response your assistant produced in this step (`model_answer`). 

At this point, you’ve built a knowledge assistant that answers questions using context retrieved from your uploaded FAQ files, and you’re ready to evaluate how well it performs.

## Task 7. Evaluate alignment with Promptfoo

In this final task, you’ll evaluate the grounded answers you generated in Task 6 with Promptfoo to quantify how well they align with your reference answers. You’ll work with the `promptfooconfig.yaml` file and use the existing `step_04_eval_results.py` entry point.

This script evaluates your model’s answers against reference answers using a grading rubric and summarizes the results with pass/fail totals. Promptfoo's local viewer provides the detailed feedback. This gives you clear, objective insight to guide further improvements.

More specifically, the script: 
- Loads the augmented dataset generated in Task 6 from `labs/data/rag_model_answer.jsonl`.
- Uses the alignment assertion in `labs/lab03_rag_guided/promptfooconfig.yaml` with the original 1–7 rating scale and pass threshold.
- Runs the saved `model_answer` values through Promptfoo's local `echo` provider, so the RAG pipeline is not called again.
- Stores results locally for item-level review, rubric scores, reasons, and raw model outputs.

Let's now see how our RAG pipelines peforms.

1. Validate the Promptfoo configuration:

```bash
node scripts/promptfoo.mjs validate config -c labs/lab03_rag_guided/promptfooconfig.yaml
```

2. Run the following command to evaluate your model answers against the expected answers:

```bash
python -m labs.lab03_rag_guided.step_04_eval_results
```

The existing Step 4 module is a small compatibility launcher. It runs the equivalent Promptfoo command with the pinned package and `--no-cache`.

**Expected output (abridged example):**
```bash
Loaded 11 items from: <bundle-root>/labs/data/rag_model_answer.jsonl
Starting evaluation ...
Running 11 test cases ...
✓ Eval complete

Results:
  ✓ <passed> passed
  <failed> failed
  0 errors
Review item-level results with: node scripts/promptfoo.mjs view
```

3. Start Promptfoo's local results viewer:

```bash
node scripts/promptfoo.mjs view
```

4. Open the URL printed by Promptfoo, select your latest Lab 03 run, and take a moment to explore:
* Item-level scores and any failing criteria
* Assertion details (rubric text), reasons, and raw model outputs
* How each normalized score maps back to the 1–7 rating and pass threshold

Congratulations! With grading complete, you’ve developed a full end-to-end RAG pipeline, following extraction → indexing → retrieval/answering → evaluation. 

You now have a measurable, and robust solution that you can improve by iterating on prompts, retrieval parameters, and rubric thresholds.

## Optional tuning and exploration

#### Agentic RAG
* If you have a few extra minutes, run the optional Agentic RAG example to wrap the vector store-backed File Search workflow in an agent built with the OpenAI Agents SDK.
* The script reuses the vector store created in Task 5 by loading `VECTOR_STORE_ID` from `labs/lab03_rag_guided/.env`. Confirm that file contains a non-empty `VECTOR_STORE_ID=vs_...` value before continuing.
* Run the command below:

    ```bash
    python -m labs.lab03_rag_guided.step_05_agent_rag "Can I get a student discount?"
    ```

* The exercise is complete when the script prints the configured model and vector store, then returns a grounded answer to the sample question.

#### Testing crtieria
* If you want to explore stricter or looser grading, open `promptfooconfig.yaml` and adjust the normalized `threshold` and matching pass instruction (or add another assertion), then rerun Task 7.
* The local `echo` provider does not make an API call. The enabled model-graded alignment assertion makes one grader call per row; the local viewer makes no additional grader calls.

#### Paramters and controls
* If you have a few minutes, feel free to extend the dataset and experiment with the controls that shape retrieval and reasoning. You can try different models and reasoning efforts, and limit coverage to a handful of items. 
* The primary controls are **`MODEL`** (e.g., gpt-5-mini), **`EFFORT`** (low, medium, high), **`NUM_QUESTIONS`** (e.g., 5), and **`MAX_NUM_RESULTS`** (e.g., `8`). 

* For example, you can set them to something like the following and rerun:

    ```bash
    export MODEL="gpt-5-mini"
    export EFFORT="high"
    export NUM_QUESTIONS=5
    export MAX_NUM_RESULTS=8
    export RAG_DATA_FILE="labs/data/sample_01.jsonl"
    export RAG_OUTPUT_FILE="labs/data/rag_model_answer.jsonl"
    python -m labs.lab03_rag_guided.step_03_run_questions
    ```

With these adjustments you can see how retrieval depth, latency, and model reasoning change grounding quality and answer usefulness.

### Finished already? That was quick!


## Conclusion

### Wrap‑Up
In this lab, you built an end-to-end RAG pipeline and workflow from start to finish:
1. Set up your Python environment and installed all required dependencies.
2. Indexed your FAQ data and created a vector store for retrieval.
3. Developed and ran a retrieval-augmented generation (RAG) pipeline to answer sample questions using your indexed data.
4. Collected and formatted model answers alongside expected answers for evaluation.
5. Evaluated your RAG outputs using Promptfoo, reviewed pass/fail results, and iterated on your pipeline or rubric as needed.

**Checkpoint**: Review your item-level results and record one finding, one limitation, and one next improvement. Complete the reflection questions below.

### Discussion Prompts

Consider the following questions to reflect on your RAG pipeline design and deployment strategy:
- **Retrieval tradeoff:** How do you balance retrieval precision versus coverage when curating FAQ sources?
- **Prompt/retrieval tuning:** Which prompt or retrieval adjustments most improved grounding strength in your tests?
- **Production criteria:** What eval thresholds would you require before shipping this workflow to production support teams?

### Troubleshooting

If you encounter issues during the lab, refer to these common problems and their solutions:

- **Missing or invalid OPENAI_API_KEY:** Check credential setup in the bundle root README without printing the key and rerun the step.
- **VECTOR_STORE_ID not set:** Re-run Task 5 and confirm `labs/lab03_rag_guided/.env` includes `VECTOR_STORE_ID=...` before Task 6.
- **No items indexed:** Ensure `labs/data/faq_example.jsonl` exists and contains valid JSONL lines (rerun Task 4 if needed).
- **No questions processed:** Inspect `labs/data/sample_01.jsonl` and confirm each line wraps data under an `item` key: `{"item": {"input": "..."}}`
- **Unsupported Node.js runtime:** Install Node.js 24 LTS, then rerun the pinned Promptfoo command.
- **Promptfoo grader error:** Confirm `OPENAI_API_KEY` is set and its project can use `gpt-5`.
