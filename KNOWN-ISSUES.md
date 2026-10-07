# Verification and known limitations

**Security update:** Supporting dependency pins, the local viewer launcher, and evaluation error classification were updated after the live runs described below. Those historical live results do not constitute a new live test of this archive. The security update is verified with fresh installations, offline SDK checks, recorded-result replay, and local viewer tests. Models, scoring criteria, reference datasets, and unfinished exercises are preserved.

On 2026-09-01, the completed guide ran live: 106 FAQ items were extracted and indexed in a fresh store, all 11 supplied questions received answers, and the unchanged GPT-5 grader passed 8/11 with no runtime/grader errors. The three failures concerned expected answers conflicting with the FAQ. Direct and agentic fallback tests acknowledged missing evidence, although they offered follow-up actions beyond this lab’s capabilities. All 106 uploaded files and the store were deleted and confirmed absent. Models and scoring criteria remain unchanged.

- Indexing submission is asynchronous and catches some upload errors. Verify successful attachment counts/statuses in Storage, not just the final console message.
- `RAG_DATA_FILE` and `RAG_OUTPUT_FILE` now honor the settings already documented in the guide. Other exercise behavior is preserved.
- The extraction preview shows the first three items, not necessarily the newly added Sustainability & Ethics items. Inspect the entire generated JSONL to confirm additions.
- Generated answers and rubric scores can vary. An unsupported question should receive an explicit limitation based on the files. Do not treat an error string or empty output as a successful fallback.
- Storage persists after local processes stop. Follow the root README cleanup for the new store and its underlying uploaded files.

All starter TODOs remain. Generated answers, evaluation histories, credentials, prior resource IDs, and unrelated labs are excluded. Windows and Linux instructions were reviewed, not runtime-tested on those systems. The verification host was macOS with Python 3.13.0 and Node 24.19.0; Python 3.12 was not executed.

The standard [MIT license](LICENSE) was added at the packaging requester’s direction; original source attribution is retained in [ATTRIBUTION.md](ATTRIBUTION.md).
