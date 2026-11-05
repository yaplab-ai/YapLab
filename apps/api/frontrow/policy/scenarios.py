"""Synthetic, deterministic policy exercises with staged, role-specific disclosure.

Exercises live only in the current application process. IDs are bearer capabilities,
not authentication; these scenarios and decision summaries must not contain real
student information. No transcripts or automated role judgments are stored.
"""
from __future__ import annotations

import json
import hashlib
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from frontrow.limits import DemoLimits, LimitExceeded, client_ip
from .diagnostics import VALIDATION_ISSUES
from .audit import seal, render_html

Role = Literal["teacher", "privacy", "accessibility"]
ROLES = ("teacher", "privacy", "accessibility")
EXERCISE_TTL_SECONDS = 3600
MAX_EXERCISES = 200
MAX_ACTIONS = 100
MAX_DECISION_LENGTH = 500
MAX_COORDINATION_BYTES = 65536
INSTITUTIONS = ("general", "uaeu")
_EVIDENCE_FIELDS = ("id", "title", "url", "authority", "jurisdiction", "document_type", "scope", "summary", "limitations", "institution")
_OPTIONAL_EVIDENCE_FIELDS = ("source_locator", "verification")
_HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _validate_provenance(result: dict, item: dict) -> None:
    """Require bounded, structured references; never treat model prose as provenance."""
    for key in ("protocol_version", "corpus_version"):
        if not isinstance(result.get(key), str) or not 0 < len(result[key]) <= 128:
            raise ValueError("invalid version")
    model = result.get("model")
    if not isinstance(model, dict) or set(model) != {"provider", "model"}:
        raise ValueError("invalid model metadata")
    if any(not isinstance(model.get(key), str) or not 0 < len(model[key]) <= 128 for key in ("provider", "model")):
        raise ValueError("invalid model metadata")
    digest = item.get("prompt_sha256")
    if not isinstance(digest, str) or not _HEX_DIGEST.fullmatch(digest) or type(item.get("prompt_attempted")) is not bool:
        raise ValueError("invalid prompt provenance")
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 3:
        raise ValueError("invalid evidence")
    evidence_ids = set()
    for source in evidence:
        if (not isinstance(source, dict) or not {*_EVIDENCE_FIELDS, "sha256"} <= set(source)
                or set(source) - {*_EVIDENCE_FIELDS, *_OPTIONAL_EVIDENCE_FIELDS, "sha256"}):
            raise ValueError("invalid source fields")
        if any(not isinstance(source[key], str) or not 0 < len(source[key]) <= 4000
               for key in _EVIDENCE_FIELDS if key not in ("limitations", "institution")):
            raise ValueError("invalid source metadata")
        if any(not isinstance(source[key], str) or not 0 < len(source[key]) <= 4000
               for key in _OPTIONAL_EVIDENCE_FIELDS if key in source):
            raise ValueError("invalid source metadata")
        if source["institution"] not in (None, "uaeu"):
            raise ValueError("invalid source institution")
        limits = source["limitations"]
        if not isinstance(limits, list) or len(limits) > 12 or any(not isinstance(value, str) or len(value) > 4000 for value in limits):
            raise ValueError("invalid source limitations")
        if source["id"] in evidence_ids:
            raise ValueError("duplicate source")
        evidence_ids.add(source["id"])
        canonical = json.dumps({key: value for key, value in source.items() if key != "sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if source["sha256"] != hashlib.sha256(canonical.encode("utf-8")).hexdigest():
            raise ValueError("source digest mismatch")
    for proposal in item.get("proposals", []):
        source_ids = proposal.get("source_ids") if isinstance(proposal, dict) else None
        if not isinstance(source_ids, list) or any(not isinstance(source_id, str) or source_id not in evidence_ids for source_id in source_ids):
            raise ValueError("proposal source not in role evidence")

# The source file contains invented case facts, never submitted transcripts.
_SCENARIOS = json.loads(Path(__file__).with_name("scenarios.json").read_text(encoding="utf-8"))
_BY_ID = {scenario["id"]: scenario for scenario in _SCENARIOS}

router = APIRouter(prefix="/policy", tags=["policy exercises"])
_init_lock = threading.Lock()


class CreateExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=80)


class AdvanceExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_stage: int = Field(strict=True, ge=1)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role
    decision: str = Field(min_length=1, max_length=MAX_DECISION_LENGTH)
    source_ids: list[str] = Field(min_length=1, max_length=12)
    expected_stage: int = Field(strict=True, ge=1)

    @field_validator("decision")
    @classmethod
    def nonblank_decision(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("decision must not be blank")
        return value

    @field_validator("source_ids")
    @classmethod
    def valid_source_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not x or len(x) > 80 for x in value):
            raise ValueError("source_ids must be unique nonempty fact IDs")
        return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExerciseStore:
    """Bounded in-memory store; all operations and cleanup are serialized."""

    def __init__(self, *, ttl: float = EXERCISE_TTL_SECONDS,
                 capacity: int = MAX_EXERCISES, max_actions: int = MAX_ACTIONS,
                 clock=time.monotonic):
        self.ttl = ttl
        self.capacity = capacity
        self.max_actions = max_actions
        self.clock = clock
        self.lock = threading.Lock()
        self.exercises: dict[str, dict] = {}

    def _expire(self) -> None:
        now = self.clock()
        for exercise_id, exercise in list(self.exercises.items()):
            if now >= exercise["expires_at"]:
                del self.exercises[exercise_id]

    def _get(self, exercise_id: str) -> dict:
        self._expire()
        exercise = self.exercises.get(exercise_id)
        if exercise is None:
            raise HTTPException(status_code=404, detail="Exercise not found or expired")
        return exercise

    @staticmethod
    def _view(exercise_id: str, exercise: dict, role: Role) -> dict:
        scenario = _BY_ID[exercise["scenario_id"]]
        stages = []
        for number, stage in enumerate(scenario["stages"][:exercise["current_stage"]], 1):
            facts = []
            for fact in stage["facts"]:
                if role in fact["roles"]:
                    visible = {"id": fact["id"], "text": fact["text"]}
                    if "policy_source_ids" in fact:
                        visible["policy_source_ids"] = list(fact["policy_source_ids"])
                    facts.append(visible)
            stages.append({"stage": number, "title": stage["title"], "facts": facts})
        return {"exercise_id": exercise_id, "scenario_id": exercise["scenario_id"],
                "current_stage": exercise["current_stage"], "stage_count": len(scenario["stages"]),
                "role": role, "released_stages": stages}

    def create(self, scenario_id: str, role: Role) -> dict:
        with self.lock:
            self._expire()
            if scenario_id not in _BY_ID:
                raise HTTPException(status_code=404, detail="Scenario not found")
            if len(self.exercises) >= self.capacity:
                raise HTTPException(status_code=429, detail="Exercise capacity reached")
            exercise_id = secrets.token_urlsafe(24)
            while exercise_id in self.exercises:
                exercise_id = secrets.token_urlsafe(24)
            exercise = {"scenario_id": scenario_id, "current_stage": 1,
                        "expires_at": self.clock() + self.ttl, "created_at": _now_iso(), "events": [],
                        "coordination_pending": None, "coordination_results": {}}
            self.exercises[exercise_id] = exercise
            return self._view(exercise_id, exercise, role)

    def view(self, exercise_id: str, role: Role) -> dict:
        with self.lock:
            return self._view(exercise_id, self._get(exercise_id), role)

    @staticmethod
    def _check_stage(exercise: dict, expected_stage: int) -> None:
        if expected_stage != exercise["current_stage"]:
            raise HTTPException(status_code=409, detail="Stage changed; refresh the exercise before retrying.")

    def _check_action_capacity(self, exercise: dict) -> None:
        if len(exercise["events"]) + int(exercise["coordination_pending"] is not None) >= self.max_actions:
            raise HTTPException(status_code=429, detail="Exercise action limit reached")

    def advance(self, exercise_id: str, role: Role, expected_stage: int) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            self._check_stage(exercise, expected_stage)
            if exercise["current_stage"] >= len(_BY_ID[exercise["scenario_id"]]["stages"]):
                raise HTTPException(status_code=409, detail="Exercise is already at its final stage")
            self._check_action_capacity(exercise)
            exercise["current_stage"] += 1
            exercise["events"].append({"type": "advance", "stage": exercise["current_stage"], "at": _now_iso()})
            return self._view(exercise_id, exercise, role)

    def decide(self, exercise_id: str, decision: Decision) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            self._check_stage(exercise, decision.expected_stage)
            visible = self._view(exercise_id, exercise, decision.role)
            valid_ids = {fact["id"] for stage in visible["released_stages"] for fact in stage["facts"]}
            if not set(decision.source_ids).issubset(valid_ids):
                raise HTTPException(status_code=422, detail="source_ids must refer to released facts visible to this role")
            self._check_action_capacity(exercise)
            event = {"type": "decision", "review_mode": "human_decision", "stage": exercise["current_stage"], "role": decision.role,
                     "decision": decision.decision, "source_ids": list(decision.source_ids), "at": _now_iso()}
            exercise["events"].append(event)
            return {"event": dict(event)}

    def reserve_coordination(self, exercise_id: str, expected_stage: int, institution: str,
                             reuse_completed: bool = False) -> dict:
        """Return a detached saved result or reserve a released-facts-only snapshot."""
        with self.lock:
            exercise = self._get(exercise_id)
            self._check_stage(exercise, expected_stage)
            if institution not in INSTITUTIONS:
                raise HTTPException(status_code=422, detail="Unknown institution")
            completed = next((event for event in exercise["events"]
                              if event["type"] == "coordination" and event["stage"] == expected_stage
                              and event["institution"] == institution), None)
            if completed is not None:
                if reuse_completed:
                    result = exercise["coordination_results"][completed["round_id"]]
                    return {"completed_result": json.loads(json.dumps(result))}
                raise HTTPException(status_code=409, detail="A coordination round already exists for this stage and institution")
            if exercise["coordination_pending"] is not None:
                raise HTTPException(status_code=409, detail="A coordination round is already in progress")
            self._check_action_capacity(exercise)
            role_views = {}
            for role in ROLES:
                view = self._view(exercise_id, exercise, role)
                role_views[role] = [fact for stage in view["released_stages"] for fact in stage["facts"]]
            round_id = secrets.token_urlsafe(24)
            exercise["coordination_pending"] = {
                "round_id": round_id, "stage": expected_stage, "institution": institution,
                "fact_ids": {role: {fact["id"] for fact in facts} for role, facts in role_views.items()},
            }
            return {"round_id": round_id, "exercise_id": exercise_id, "scenario_id": exercise["scenario_id"],
                    "stage": expected_stage, "institution": institution, "role_views": role_views}

    def commit_coordination(self, exercise_id: str, round_id: str, result: dict) -> dict:
        """Commit a bounded result only while the reserved stage remains current."""
        with self.lock:
            exercise = self._get(exercise_id)
            pending = exercise["coordination_pending"]
            if pending is None or pending["round_id"] != round_id:
                raise HTTPException(status_code=404, detail="Coordination reservation not found")
            if pending["stage"] != exercise["current_stage"]:
                exercise["coordination_pending"] = None
                raise HTTPException(status_code=409, detail="Stage changed; refresh the exercise before retrying.")
            try:
                encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
                if len(encoded.encode("utf-8")) > MAX_COORDINATION_BYTES:
                    raise ValueError("result too large")
                safe = json.loads(encoded)
                if not isinstance(safe, dict) or safe.get("scenario_id") != exercise["scenario_id"] or type(safe.get("stage")) is not int or safe.get("stage") != pending["stage"] or safe.get("institution") != pending["institution"]:
                    raise ValueError("result does not match reservation")
                if safe.get("review_mode") not in ("offline_test", "model_assisted"):
                    raise ValueError("invalid mode")
                roles = safe.get("roles")
                if not isinstance(roles, list) or len(roles) != len(ROLES):
                    raise ValueError("invalid roles")
                seen = set()
                for item in roles:
                    if not isinstance(item, dict) or item.get("role") not in ROLES or item["role"] in seen:
                        raise ValueError("invalid role")
                    role = item["role"]
                    seen.add(role)
                    if "validation_issue" in item:
                        issue = item["validation_issue"]
                        if (not isinstance(issue, str) or issue not in VALIDATION_ISSUES
                                or item.get("status") not in ("unavailable", "partial") or item.get("reason") != "invalid_response"):
                            raise ValueError("invalid validation issue")
                    proposals = item.get("proposals")
                    if not isinstance(proposals, list) or not isinstance(item.get("questions"), list):
                        raise ValueError("invalid assessment")
                    for proposal in proposals:
                        if not isinstance(proposal, dict) or not isinstance(proposal.get("fact_ids"), list):
                            raise ValueError("invalid proposal")
                        if not all(isinstance(fact_id, str) and fact_id in pending["fact_ids"][role]
                                   for fact_id in proposal["fact_ids"]):
                            raise ValueError("fact not visible to role")
                    _validate_provenance(safe, item)
                safe["round_id"] = round_id
            except (TypeError, ValueError, OverflowError):
                exercise["coordination_pending"] = None
                raise HTTPException(status_code=422, detail="Invalid coordination result") from None
            exercise["coordination_results"][round_id] = safe
            exercise["coordination_pending"] = None
            exercise["events"].append({"type": "coordination", "round_id": round_id,
                                       "stage": pending["stage"], "institution": pending["institution"],
                                       "review_mode": safe["review_mode"], "protocol_version": safe["protocol_version"],
                                       "corpus_version": safe["corpus_version"], "model": dict(safe["model"]), "at": _now_iso()})
            return json.loads(json.dumps(safe))

    def release_coordination(self, exercise_id: str, round_id: str) -> bool:
        """Release only the matching pending round; safe to call after commit or failure."""
        with self.lock:
            self._expire()
            exercise = self.exercises.get(exercise_id)
            if exercise is None:
                return False
            pending = exercise["coordination_pending"]
            if pending is not None and pending["round_id"] == round_id:
                exercise["coordination_pending"] = None
                return True
            return False

    def get_coordination(self, exercise_id: str, round_id: str) -> dict:
        """Return the complete facilitator view, detached from the store."""
        with self.lock:
            exercise = self._get(exercise_id)
            result = exercise["coordination_results"].get(round_id)
            if result is None:
                raise HTTPException(status_code=404, detail="Coordination round not found")
            return json.loads(json.dumps(result))

    def audit(self, exercise_id: str, role: Role) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            events = []
            for event in exercise["events"]:
                if event["type"] == "advance" or (event["type"] == "decision" and event["role"] == role):
                    events.append(dict(event))
                elif event["type"] == "coordination":
                    result = exercise["coordination_results"][event["round_id"]]
                    item = next(item for item in result["roles"] if item["role"] == role)
                    assessment = {key: item[key] for key in ("role", "status", "proposals", "questions") if key in item}
                    if item.get("reason") in ("insufficient_evidence", "timeout", "invalid_response", "validation_error", "provider_error", "overall_timeout"):
                        assessment["reason"] = item["reason"]
                    if "validation_issue" in item:
                        assessment["validation_issue"] = item["validation_issue"]
                    assessment["prompt_sha256"] = item["prompt_sha256"]
                    assessment["prompt_attempted"] = item["prompt_attempted"]
                    assessment["evidence"] = [
                        {key: source[key] for key in (*_EVIDENCE_FIELDS, *_OPTIONAL_EVIDENCE_FIELDS, "sha256") if key in source}
                        for source in item["evidence"]
                    ]
                    assessment["proposals"] = [
                        {key: proposal[key] for key in ("action_id", "owner", "text", "fact_ids", "source_ids", "rationale", "rationale_rejected", "rationale_issue") if key in proposal}
                        for proposal in item["proposals"]
                    ]
                    assessment["questions"] = [
                        {key: question[key] for key in ("question_id", "text") if key in question}
                        for question in item["questions"] if isinstance(question, dict)
                    ]
                    events.append(json.loads(json.dumps({**event, "assessment": assessment})))
            return {"exercise_id": exercise_id, "events": events}


    def timeline(self, exercise_id: str) -> dict:
        """Facilitator export, in event order; no prompts or private reasoning."""
        with self.lock:
            exercise = self._get(exercise_id)
            scenario = _BY_ID[exercise['scenario_id']]
            events, rounds = [], []
            def release(stage, at):
                facts = scenario['stages'][stage - 1]['facts']
                views = {role: [{k: v for k, v in fact.items() if k != 'roles'}
                                for fact in facts if role in fact['roles']] for role in ROLES}
                events.append({'type': 'stage_release', 'stage': stage, 'at': at,
                               'fact_ids_by_role': {role: [fact['id'] for fact in views[role]] for role in ROLES},
                               'views': views})
            release(1, exercise['created_at'])
            for event in exercise['events']:
                if event['type'] == 'advance':
                    release(event['stage'], event['at'])
                elif event['type'] == 'decision':
                    events.append(dict(event))
                elif event['type'] == 'coordination':
                    result = exercise['coordination_results'][event['round_id']]
                    rounds.append(result)
                    for role in result['roles']:
                        events.append({'type': 'model_request', 'stage': event['stage'], 'at': role.get('started_at') or event['at'],
                                       'role': role['role'], **result['model'], 'review_mode': result['review_mode'],
                                       'protocol_version': result['protocol_version'], 'corpus_version': result['corpus_version'],
                                       'prompt_sha256': role['prompt_sha256'], 'prompt_attempted': role['prompt_attempted'],
                                       'usage': role.get('usage'), 'latency_ms': role.get('latency_ms'),
                                       'status': role.get('provider_status') or ('unobserved' if role['prompt_attempted'] else 'not_attempted'),
                                       'role_status': role['status'],
                                       'evidence_refs': [{'id': source['id'], 'sha256': source['sha256']}
                                                         for source in role['evidence']]})
                        events.append({'type': 'validation', 'stage': event['stage'], 'at': role.get('finished_at') or event['at'],
                                       'role': role['role'], 'status': role['status'], 'issue': role.get('validation_issue'),
                                       'rationale_issues': [p['rationale_issue'] for p in role['proposals'] if p.get('rationale_rejected')]})
                    events.append({'type': 'coordinator_plan', 'stage': event['stage'], 'at': event['at'],
                                   'plan': result['plan'], 'unresolved': result['unresolved'],
                                   'round_id': event['round_id']})
            events.sort(key=lambda item: item['at'])
            return seal(json.loads(json.dumps({'version': '1', 'exercise_id': exercise_id,
                'scenario_id': exercise['scenario_id'], 'current_stage': exercise['current_stage'],
                'events': events, 'rounds': rounds}, ensure_ascii=False)))


def _store(request: Request) -> ExerciseStore:
    with _init_lock:
        if not hasattr(request.app.state, "policy_exercise_store"):
            request.app.state.policy_exercise_store = ExerciseStore()
        return request.app.state.policy_exercise_store


class _Admission:
    """Per-app limits, serialized because sync endpoints run in worker threads."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.creates = DemoLimits(sessions_per_ip_per_hour=30, max_sessions_per_day=10000)
        self.requests = DemoLimits(sessions_per_ip_per_hour=240, max_sessions_per_day=20000)

    def admit(self, request: Request, *, create: bool = False) -> None:
        address = client_ip(request.client.host if request.client else None,
                            request.headers.get("x-forwarded-for"))
        with self.lock:
            try:
                (self.creates if create else self.requests).reserve_session(address).commit()
            except LimitExceeded as exc:
                raise HTTPException(status_code=429, detail="Exercise request limit reached; please try again later.",
                                    headers={"Retry-After": str(exc.retry_after)}) from exc


def _admit(request: Request, *, create: bool = False) -> None:
    with _init_lock:
        if not hasattr(request.app.state, "policy_exercise_admission"):
            request.app.state.policy_exercise_admission = _Admission()
        admission = request.app.state.policy_exercise_admission
    admission.admit(request, create=create)


@router.get("/scenarios")
def list_scenarios() -> dict:
    return {"scenarios": [{"id": s["id"], "title": s["title"], "summary": s["summary"],
                            "stage_count": len(s["stages"]), "roles": list(ROLES)} for s in _SCENARIOS],
            "disclaimer": "Synthetic, deterministic teaching simulation. Roles are selectable views, not autonomous agents or access controls; decisions are human-recorded. Use no real student information. Verify applicable institutional rules and law."}


@router.post("/exercises")
def create_exercise(body: CreateExercise, request: Request, response: Response, role: Role = Query(default="teacher")) -> dict:
    _admit(request, create=True)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).create(body.scenario_id, role)


@router.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: str, request: Request, response: Response, role: Role = Query(default="teacher")) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).view(exercise_id, role)


@router.post("/exercises/{exercise_id}/advance")
def advance_exercise(exercise_id: str, body: AdvanceExercise, request: Request, response: Response, role: Role = Query(default="teacher")) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).advance(exercise_id, role, body.expected_stage)


@router.post("/exercises/{exercise_id}/decision")
def record_decision(exercise_id: str, body: Decision, request: Request, response: Response) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).decide(exercise_id, body)


@router.get("/exercises/{exercise_id}/audit")
def get_audit(exercise_id: str, request: Request, response: Response, role: Role = Query(default="teacher")) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).audit(exercise_id, role)


@router.get("/exercises/{exercise_id}/timeline")
def get_timeline(exercise_id: str, request: Request, response: Response) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).timeline(exercise_id)


@router.get("/exercises/{exercise_id}/timeline.html")
def get_timeline_html(exercise_id: str, request: Request) -> Response:
    _admit(request)
    return Response(render_html(_store(request).timeline(exercise_id)), media_type="text/html",
                    headers={"Cache-Control": "no-store", "Content-Disposition": "attachment; filename=yaplab-audit.html"})
