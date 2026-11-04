"""Synthetic, deterministic policy exercises with staged, role-specific disclosure.

Exercises live only in the current application process. IDs are bearer capabilities,
not authentication; these scenarios and decision summaries must not contain real
student information. No transcripts or automated role judgments are stored.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator

from frontrow.limits import DemoLimits, LimitExceeded, client_ip

Role = Literal["teacher", "privacy", "accessibility"]
ROLES = ("teacher", "privacy", "accessibility")
EXERCISE_TTL_SECONDS = 3600
MAX_EXERCISES = 200
MAX_ACTIONS = 100
MAX_DECISION_LENGTH = 500

# The source file contains invented case facts, never submitted transcripts.
_SCENARIOS = json.loads(Path(__file__).with_name("scenarios.json").read_text(encoding="utf-8"))
_BY_ID = {scenario["id"]: scenario for scenario in _SCENARIOS}

router = APIRouter(prefix="/policy", tags=["policy exercises"])
_init_lock = threading.Lock()


class CreateExercise(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=80)


class Decision(BaseModel):
    role: Role
    decision: str = Field(min_length=1, max_length=MAX_DECISION_LENGTH)
    source_ids: list[str] = Field(default_factory=list, max_length=12)

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
                        "expires_at": self.clock() + self.ttl, "events": []}
            self.exercises[exercise_id] = exercise
            return self._view(exercise_id, exercise, role)

    def view(self, exercise_id: str, role: Role) -> dict:
        with self.lock:
            return self._view(exercise_id, self._get(exercise_id), role)

    def advance(self, exercise_id: str, role: Role) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            if exercise["current_stage"] >= len(_BY_ID[exercise["scenario_id"]]["stages"]):
                raise HTTPException(status_code=409, detail="Exercise is already at its final stage")
            if len(exercise["events"]) >= self.max_actions:
                raise HTTPException(status_code=429, detail="Exercise action limit reached")
            exercise["current_stage"] += 1
            exercise["events"].append({"type": "advance", "stage": exercise["current_stage"], "at": _now_iso()})
            return self._view(exercise_id, exercise, role)

    def decide(self, exercise_id: str, decision: Decision) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            visible = self._view(exercise_id, exercise, decision.role)
            valid_ids = {fact["id"] for stage in visible["released_stages"] for fact in stage["facts"]}
            if not set(decision.source_ids).issubset(valid_ids):
                raise HTTPException(status_code=422, detail="source_ids must refer to released facts visible to this role")
            if len(exercise["events"]) >= self.max_actions:
                raise HTTPException(status_code=429, detail="Exercise action limit reached")
            event = {"type": "decision", "review_mode": "human_decision", "stage": exercise["current_stage"], "role": decision.role,
                     "decision": decision.decision, "source_ids": list(decision.source_ids), "at": _now_iso()}
            exercise["events"].append(event)
            return {"event": dict(event)}

    def audit(self, exercise_id: str, role: Role) -> dict:
        with self.lock:
            exercise = self._get(exercise_id)
            # Return copies; only the requesting role's submitted text is disclosed.
            events = [dict(e) for e in exercise["events"] if e["type"] == "advance" or e["role"] == role]
            return {"exercise_id": exercise_id, "events": events}


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
def advance_exercise(exercise_id: str, request: Request, response: Response, role: Role = Query(default="teacher")) -> dict:
    _admit(request)
    response.headers["Cache-Control"] = "no-store"
    return _store(request).advance(exercise_id, role)


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
