"""Record a reproducible OFFLINE Policy Lab walkthrough, never provider results.

From apps/api: .venv/bin/python scripts/evaluate_policy.py
The output contains synthetic cases and software observations, not real learners.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(API_ROOT))
for key, value in {
    "FRONTROW_LLM": "fake",
    "FRONTROW_POLICY_LLM": "off",
    "FRONTROW_TTS": "none",
    "FRONTROW_STT": "none",
}.items():
    os.environ[key] = value

from fastapi.testclient import TestClient
from frontrow.server import create_app

PROBES = [
    ("Can we keep recordings with learner names?", {"uae-personal-data-protection"}),
    ("Captions failed and a screen reader cannot read the slides.",
     {"uae-persons-with-disabilities-education"}),
    ("Can AI feedback decide a course grade?",
     {"unesco-generative-ai-education", "england-generative-ai-education"}),
    ("quasar xylophone marsupial", set()),
]


def checked(response):
    response.raise_for_status()
    return response.json()


def evaluate() -> dict:
    result = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": "local TestClient, offline fake classroom, deterministic policy review",
        "limitations": [
            "Hand-authored smoke probes check software behavior, not retrieval accuracy on a representative dataset.",
            "No live policy model, educator study, legal review or ITU-hosted KB import was evaluated.",
            "Roles are selectable simulation views, not authenticated institutional agents.",
        ],
        "retrieval_probes": [],
        "scenario_walkthroughs": [],
    }
    with TestClient(create_app()) as client:
        corpus = checked(client.get("/policy/sources"))
        source_ids = {entry["id"] for entry in corpus["entries"]}
        result["corpus_version"] = corpus["version"]
        result["source_count"] = len(source_ids)
        institutional = checked(client.get("/policy/sources", params={"institution": "uaeu"}))
        result["reference_collection_counts"] = {"general": len(source_ids), "uaeu": len(institutional["entries"])}
        scoped_query = "UAEU syllabus GenAI assessment"
        scoped_hits = {}
        for scope in ("general", "uaeu"):
            found = checked(client.post("/policy/search", json={"query": scoped_query, "limit": 10, "institution": scope}))
            scoped_hits[scope] = [item["id"] for item in found["results"]]
        assert not any(item.startswith("uaeu-") for item in scoped_hits["general"])
        assert "uaeu-student-generative-ai" in scoped_hits["uaeu"]
        result["institution_scope_probe"] = {"query": scoped_query, "observed_source_ids": scoped_hits,
                                             "excluded_from_general": True, "passed": True}
        for query, expected in PROBES:
            data = checked(client.post("/policy/search", json={"query": query, "limit": 3}))
            actual = [entry["id"] for entry in data["results"]]
            passed = bool(set(actual) & expected) if expected else not actual
            result["retrieval_probes"].append({
                "query": query, "expected_any_in_top_3": sorted(expected),
                "observed_source_ids": actual, "passed": passed,
            })
        scenarios = checked(client.get("/policy/scenarios"))["scenarios"]
        for scenario in scenarios:
            exercise = checked(client.post("/policy/exercises", json={"scenario_id": scenario["id"]}))
            exercise_id = exercise["exercise_id"]
            case = {"scenario_id": scenario["id"], "stages": []}
            for stage in range(1, scenario["stage_count"] + 1):
                observations = {}
                for role in scenario["roles"]:
                    view = checked(client.get(f"/policy/exercises/{exercise_id}", params={"role": role}))
                    assert view["current_stage"] == stage
                    assert all(item["stage"] <= stage for item in view["released_stages"])
                    facts = [fact for item in view["released_stages"] for fact in item["facts"]]
                    linked = {sid for fact in facts for sid in fact.get("policy_source_ids", [])}
                    assert linked <= source_ids, "Scenario references a source outside the corpus"
                    text = "\n".join(fact["text"] for fact in facts)
                    reviewed = checked(client.post("/policy/review", json={"text": text}))
                    assert reviewed["review_mode"] == "deterministic"
                    assert set(reviewed["audit"]["source_ids"]) <= source_ids
                    observations[role] = {
                        "visible_fact_ids": [fact["id"] for fact in facts],
                        "linked_policy_source_ids": sorted(linked),
                        "review_mode": reviewed["review_mode"],
                        "review_citation_ids": reviewed["audit"]["source_ids"],
                        "topics": reviewed["audit"]["selected_topics"],
                    }
                case["stages"].append({"stage": stage, "role_observations": observations})
                checked(client.post(f"/policy/exercises/{exercise_id}/decision", json={
                    "role": "teacher", "decision": "Pause the simulated activity and confirm the institutional process before continuing.",
                }))
                if stage < scenario["stage_count"]:
                    checked(client.post(f"/policy/exercises/{exercise_id}/advance"))
            audit = checked(client.get(f"/policy/exercises/{exercise_id}/audit"))
            case["teacher_audit_event_count"] = len(audit["events"])
            result["scenario_walkthroughs"].append(case)
    result["all_retrieval_probes_passed"] = all(item["passed"] for item in result["retrieval_probes"])
    return result


if __name__ == "__main__":
    evidence = evaluate()
    output = REPO_ROOT / "docs" / "evidence" / "ai-for-good-offline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(evidence['scenario_walkthroughs'])} staged walkthroughs and "
          f"{len(evidence['retrieval_probes'])} retrieval smoke probes in {output}")
    if not evidence["all_retrieval_probes_passed"]:
        print("Some retrieval smoke probes did not retrieve the expected source; inspect the evidence.")
        raise SystemExit(1)
