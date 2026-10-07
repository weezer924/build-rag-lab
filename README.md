# Build with Retrieval-Augmented Generation

OpenAI Academy · standalone guided lab

This bundle contains the guided exercise, its required data, and the existing reference material. You do not need to clone a repository or obtain another course bundle.

**Verification:** The original guided workflows received bounded live checks on macOS. This security update is checked separately with offline compatibility and security tests; it has not received a new paid end-to-end run. See [results and known limitations](KNOWN-ISSUES.md), including operating systems not runtime-tested. The standard MIT license is included at the packaging requester’s direction.

## 1. Download and extract

Download `build-with-retrieval-augmented-generation-guided-lab.zip`. Extract it using your file manager, then open a terminal in the extracted `build-with-retrieval-augmented-generation-guided-lab` directory. That directory contains this README, `requirements.txt`, and `labs/` and is called the **bundle root** throughout the instructions. Do not run commands inside the ZIP or from the inner lab folder.

From the folder containing the downloaded ZIP, macOS/Linux:

```bash
unzip build-with-retrieval-augmented-generation-guided-lab.zip
cd build-with-retrieval-augmented-generation-guided-lab
```

Windows PowerShell:

```powershell
Expand-Archive -LiteralPath .\build-with-retrieval-augmented-generation-guided-lab.zip -DestinationPath .
Set-Location .\build-with-retrieval-augmented-generation-guided-lab
```

## 2. Prerequisites and installation

- Python **3.12 or 3.13**. The original guides said 3.10+, but the source manifest requires 3.12+. Use the documented versions for this bundle.
- Node.js **24 LTS**, including npm. Promptfoo remains **0.121.18**; `package-lock.json` fixes the dependency versions used by this bundle.
- A text editor and browser. The macOS/Linux preview commands use `jq`; install it with your OS package manager, or use the Python JSON preview below. PowerShell examples do not require jq.
- Internet access to install dependencies, plus an OpenAI API project with billing, a project-scoped API key, and access to the models listed below. ChatGPT subscriptions do not configure this API key or project.

Create a new virtual environment in this bundle; do not reuse another lab's environment.

macOS/Linux:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
export PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo"
node --version
npm ci --ignore-scripts --registry=https://registry.npmjs.org
node scripts/promptfoo.mjs --version
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PROMPTFOO_PYTHON = (Join-Path (Get-Location) '.venv\Scripts\python.exe')
$env:PROMPTFOO_CONFIG_DIR = (Join-Path (Get-Location) '.promptfoo')
node --version
npm ci --ignore-scripts --registry=https://registry.npmjs.org
node scripts/promptfoo.mjs --version
```

If you installed Python 3.13 on Windows, use `py -3.13` for the first command. If PowerShell blocks virtual-environment activation, invoke `.\.venv\Scripts\python.exe` wherever the guide says `python` and keep the `PROMPTFOO_PYTHON` setting above; no execution-policy change is required. Where PowerShell blocks `npm.ps1`, use `npm.cmd ci --ignore-scripts --registry=https://registry.npmjs.org`.

`requirements.txt` pins the direct dependencies and applies `constraints.txt`. Security fixes update supporting libraries while preserving the course’s OpenAI SDK versions. `npm ci --ignore-scripts --registry=https://registry.npmjs.org` installs the exact Node dependency tree and verifies its package integrity hashes. Install scripts are disabled; optional local-model integrations outside this lab are not configured. No global Promptfoo installation is needed. Run Promptfoo through `node scripts/promptfoo.mjs` as shown in the guide; it uses only this bundle’s installation.

The viewer binds only to `127.0.0.1` and rejects requests from unrelated websites. Open the localhost URL it prints and stop it with Ctrl+C. Do not launch a separate bare `promptfoo view` command or expose the viewer on a network. If port 15500 is occupied, set `API_PORT` to another unused port before starting the viewer.

Promptfoo is a third-party tool with usage telemetry. The bundle launcher disables normal telemetry and update checks; this Promptfoo version may still send a telemetry-disabled event with runtime/user metadata. Do not assume complete offline operation or add real customer information to the sample data.

## 3. Credentials and local results

Copy the safe template, then open **the new root `.env` file in your editor** and fill in `OPENAI_API_KEY` with your own project-scoped key. Never paste it into a screenshot or print it in a terminal. Do not share the filled file.

macOS/Linux:

```bash
cp .env.example .env
chmod 600 .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

The Python scripts and Promptfoo load the root `.env`. Direct Python snippets in the guided Agents lab also load it explicitly. Use a fresh terminal, without inherited `OPENAI_API_KEY`, `OPENAI_BASE_URL`, model overrides, or vector-store IDs from another project. A project-scoped key normally needs no organization or project override. If your organization requires one, use the environment names supported by the installed SDK (`OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`) and configure Promptfoo consistently; verify the selected project before running.

From the bundle root, check installation and whether a key is present **without revealing it**:

```bash
python scripts/check_setup.py
```

This performs local checks only. “Key present” does not establish model access. Before paid steps, confirm the selected API project allows the specified models and endpoints. A 401 means authentication failed; a 403 or model-not-found error may mean missing model/project permission. Resolve access instead of silently substituting a model.

The bundle launcher fixes `PROMPTFOO_CONFIG_DIR` to this bundle’s `.promptfoo` directory for both eval and viewer commands. Set `PROMPTFOO_PYTHON` again after opening a new terminal. This keeps local results separate from other labs.

## 4. Complete the guided exercise

Read [the complete guided lab](labs/lab03_rag_guided/README.md), beginning at Task 2 after completing setup here. It preserves the original sequence, code blocks, rubrics, and checkpoints. All its commands run from this bundle root. A bare filename such as `tools.py` means the file inside `labs/lab03_rag_guided/`.

**Models:** `gpt-5-nano` for extraction, question answering, and optional agentic RAG; `gpt-5` for grading. See [GPT-5 nano](https://developers.openai.com/api/docs/models/gpt-5-nano) and [GPT-5](https://developers.openai.com/api/docs/models/gpt-5). These defaults are unchanged. File Search and Files/Vector Stores access are required; a project configuration that forbids persistent storage cannot complete indexing.

**Sequence:** Add the Sustainability & Ethics Q/A section to `faq_example.md`; fill the extraction prompt; generate FAQ JSONL; create and populate a new vector store; wait for indexing; fill the Responses call; answer the 11 supplied questions; grade answers; optionally run the self-contained agentic RAG example. Only the original FAQ markdown and question dataset ship: generated FAQ JSONL and generated answers are deliberately absent. There is no separate RAG solution file in the source; the guide supplies both replacement code blocks. The `system_msg` and Responses-call placeholders remain in the shipped starter.

A baseline run makes one extraction call, 11 question-answering calls with File Search, and 11 grader calls, plus uploads/indexing operations. The optional agent example and tuning runs add model/tool calls. `RAG_DATA_FILE` and `RAG_OUTPUT_FILE` now honor the environment settings already documented in the guide; relative paths are resolved from the bundle root.

Task 5 creates persistent resources: one vector store and approximately one uploaded file per extracted FAQ. Start with no `VECTOR_STORE_ID` override; keep the lab-local `.env` that Task 5 creates. Only reuse the store created for this bundle: rerunning indexing deletes/replaces matching uploaded files. The script submits indexing asynchronously, so verify all attachments are `completed` before asking questions. Track the created store ID and uploaded file IDs privately for cleanup.

This bundle includes only the five guided step scripts, eval adapter/config, source FAQ markdown, `sample_01.jsonl`, package initializers, setup files, and provenance. The storage screenshot containing an old resource ID is replaced by a text checkpoint.


Each step that invokes an OpenAI model incurs API usage. Dependency installation, syntax checks, data inspection, and `promptfoo validate config` do not make model calls. The local `echo` provider returns existing answers; the `llm-rubric` assertions make the paid grader calls. A viewer session adds no grader calls. Repeating an eval with `--no-cache` charges for fresh grading; transient retries can add calls. Reasoning tokens also count toward output usage.

Prices and availability can change. Check the [official API pricing page](https://developers.openai.com/api/docs/pricing) and project usage before running. If you run File Search, it currently lists $2.50 per 1,000 tool calls and $0.10 per GB per day of storage after the free allowance; do not assume your project has unused free storage.

## 5. Check your results

- Use the step-specific checkpoints in the guide. Inspect actual output, not just process exit status; some original runners catch errors and still exit successfully.
- Keep runtime/API errors separate from ordinary failed assertions. The supplied data contains deliberately questionable answers; model graders may disagree. There is no required aggregate pass count.
- Verify each expected row exists, generated answers are nonempty, and there are no `[ERROR]` outputs before evaluating. A guardrail tripwire on deliberately unsafe/off-topic input is an expected learning outcome.
- Inspect the latest local Promptfoo run and record one strong example, one failure or uncertain judgment, and one improvement. Answer the guide's reflection questions. No live facilitator is needed for completion.
- The `MANIFEST.sha256` file describes the untouched bundle. Your exercises will intentionally change starter files; keep the downloaded ZIP as your clean recovery copy.

Portable JSONL preview (replace the filename as needed):

```bash
python -c "import json; from pathlib import Path; p=next(Path('labs/data').glob('sample_*.jsonl')); print(json.dumps(json.loads(p.read_text(encoding='utf-8').splitlines()[0]), indent=2))"
```

## Troubleshooting

- `No module named labs`: return to the bundle root and use `python -m labs...`, with the bundle's environment active. Do not set `PYTHONPATH` to a repository checkout.
- Missing dependency: rerun `python -m pip install -r requirements.txt` with the same Python interpreter used by Promptfoo.
- Python/Pydantic `TypedDict` error: use Python 3.12 or 3.13 and recreate the environment.
- Invalid YAML: compare indentation with the guide/reference; validate after each edit.
- Missing generated dataset: finish the generation task first. No previous results ship in this ZIP.
- Promptfoo viewer appears empty: use the same `PROMPTFOO_CONFIG_DIR` as the eval, and complete a run first.
- API rate/quota errors: check your project's usage and limits; wait before retrying. Do not repeatedly relaunch entire workflows.
- Expected starter gaps: complete the explicit TODOs first. A placeholder response or missing tool before its implementation task is not evidence of an installation error.

Windows commands have been reviewed but not runtime-tested on Windows. Linux commands likewise have not been executed on Linux; the local verification host is macOS.

## Cleanup

Stop the viewer with Ctrl+C. Save any exercise notes you need. Delete only this bundle's `.promptfoo` directory to remove local Promptfoo results, and this bundle's `.venv` to remove its installed environment. Delete your filled `.env`, revoke the lab key in your API project when no longer needed, and clear shell overrides by closing the terminal. Keep unrelated project keys, results, files, and resources untouched.

For Agents/RAG, API responses and traces may remain in the project's platform history according to its data settings; deleting local files does not delete server-side history. The RAG-specific resource cleanup below is required separately.

Before deleting any local ID records, open [Storage](https://platform.openai.com/storage) in the same project used for this lab. Identify **only the store you created in Task 5** and record its attached file IDs. Delete that store and the underlying uploaded files created by this lab; deleting a store does not automatically delete the underlying Files objects. Also check for task-created orphan uploads if indexing failed between upload and attachment. Do not delete unrelated files or resources merely because their names resemble these examples.

Verify the task-created store and files are gone, then remove this bundle's `labs/lab03_rag_guided/.env`. Clear `VECTOR_STORE_ID` from the shell if set. Deleting the local ID file alone does not stop storage charges. Store creation in the original script sets no automatic expiration, so storage persists until deletion or an expiration policy you configure. Consult [the retrieval guide](https://developers.openai.com/api/docs/guides/retrieval) for storage lifecycle details.


See [attribution and license](ATTRIBUTION.md), [known issues](KNOWN-ISSUES.md), and `SOURCE.json` for source provenance.
