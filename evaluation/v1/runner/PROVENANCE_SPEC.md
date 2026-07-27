# Provenance Specification

Every evaluation run produces an append-only JSONL ledger.
Each line is one case x one condition x one attempt.

## Required Fields Per Record

| Field | Type | Description |
|---|---|---|
| run_id | str | Unique run identifier |
| case_id | str | Immutable case identifier |
| condition | str | original / generic / checkmycoach |
| model | str | Model identifier used |
| timestamp | str | ISO 8601 UTC |
| input_exact | dict | Exact input sent |
| evidence_ids | list[str] | Evidence object IDs |
| request_payload | dict | Full API request payload |
| raw_response | str | Raw model output text |
| structured_output | dict or null | Parsed AUDIT_JSON |
| correction_trace | dict or null | M3 diagnosis + prompt |
| validation_trace | dict or null | M4 validation result |
| ucs_score | int or null | UCS score (0-3) |
| token_usage | dict | prompt_tokens, completion_tokens, cost |
| latency_ms | float | Total latency |
| error | str or null | Error message |
| retry_count | int | Number of retries |
| included | bool | Whether included in analysis |

## Append-Only Guarantee
- Records appended to run_{run_id}.jsonl
- No record is ever overwritten or deleted
- Ledger file is hashed at run end
