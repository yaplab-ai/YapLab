"""Evidence endpoints and explicitly enabled synthetic coordination rounds."""
from __future__ import annotations

import asyncio
import math
import json
import os
import secrets
from pathlib import Path
import re
import time
from collections import deque
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from frontrow.limits import DemoLimits, LimitExceeded, client_ip
from frontrow.llm.base import LLMClient
from .audit import validate_recording, render_html
from .agent import agent_review
from .coordination import coordinate, Mode, PROTOCOL_VERSION
from .scenarios import _store
from .evidence import CorpusUnavailable, Institution, Topic, load_corpus, scoped_sources, search_with_mode
from .review import review

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
ReviewText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
ContextText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: ShortText
    limit: int = Field(default=5, ge=1, le=10, strict=True)
    institution: Institution = 'general'


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: ReviewText
    topics: list[Topic] = Field(default_factory=list, max_length=5)
    context: ContextText = ''
    institution: Institution = 'general'


# These catches are intentionally narrow; absence of a match is not a privacy
# guarantee. Do not log or store requests or matched strings.
_EMAIL = re.compile(r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b')
_PHONE = re.compile(r'(?<!\w)(?:\+\d[\d ()-]{7,}\d|0\d[\d ()-]{7,}\d)(?!\w)')


def _check_input(*parts: str) -> None:
    if any(_EMAIL.search(part) or _PHONE.search(part) for part in parts):
        raise HTTPException(422, 'Remove personal or identifying information before submitting. Automatic detection is limited.')


def _corpus():
    try:
        return load_corpus()
    except CorpusUnavailable as exc:
        raise HTTPException(503, 'Policy source notes are currently unavailable.') from exc



class CoordinationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_stage: int = Field(ge=1, le=3, strict=True)
    institution: Institution = 'general'


class ModelCallLimits:
    """Process-local paid-call cap: 8/IP/hour, 20/IP/rolling day, 100/day total."""

    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic,
                 evaluation_limit: int | None = None) -> None:
        if evaluation_limit is not None and (type(evaluation_limit) is not int or not 1 <= evaluation_limit <= 60):
            raise ValueError('Synthetic evaluation call limit must be from 1 to 60')
        self._monotonic = monotonic
        self._per_ip_day = evaluation_limit or 20
        self._hourly = DemoLimits(sessions_per_ip_per_hour=evaluation_limit or 8,
                                  max_sessions_per_day=evaluation_limit or 100, monotonic=monotonic)
        self._daily: dict[str, deque[float]] = {}

    def reserve(self, address: str, count: int = 1) -> None:
        if type(count) is not int or not 1 <= count <= 3:
            raise ValueError('Reserve between one and three model calls')
        now = self._monotonic()
        for ip, entries in list(self._daily.items()):
            while entries and entries[0] + 86400 <= now:
                entries.popleft()
            if not entries:
                del self._daily[ip]
        entries = self._daily.get(address)
        if entries and len(entries) + count > self._per_ip_day:
            raise LimitExceeded('Model review daily limit reached.', math.ceil(entries[0] + 86400 - now))
        reservations = []
        try:
            for _ in range(count):
                reservations.append(self._hourly.reserve_session(address))
        except LimitExceeded:
            for reservation in reservations:
                reservation.rollback()
            raise
        for reservation in reservations:
            reservation.commit()
        self._daily.setdefault(address, deque()).extend([now] * count)


def create_router(*, llm: LLMClient | None = None, model: str = 'gpt-4o-mini',
                  coordination_llm: LLMClient | None = None,
                  coordination_model: str | None = None,
                  coordination_mode: Mode = 'model_assisted') -> APIRouter:
    router = APIRouter(prefix='/policy', tags=['policy'])
    role_model = coordination_model or model
    # Separate from paid practice-session quotas, per FastAPI app instance.
    admission = DemoLimits(sessions_per_ip_per_hour=120, max_sessions_per_day=10000)
    # Explicit local synthetic-evaluation allowance; production defaults stay unchanged.
    evaluation_limit = os.environ.get('FRONTROW_POLICY_EVALUATION_CALL_LIMIT')
    model_admission = ModelCallLimits(evaluation_limit=int(evaluation_limit) if evaluation_limit else None)
    model_slots = asyncio.Semaphore(2)
    recordings: dict[str, dict] = {}

    def admit(request: Request) -> None:
        address = client_ip(request.client.host if request.client else None,
                            request.headers.get('x-forwarded-for'))
        try:
            admission.reserve_session(address).commit()
        except LimitExceeded as exc:
            raise HTTPException(429, 'Policy request limit reached; please try again later.',
                                headers={'Retry-After': str(exc.retry_after)}) from exc

    @router.get('/sources')
    async def sources(request: Request, response: Response, institution: Institution = 'general'):
        admit(request)
        corpus = _corpus()
        response.headers['Cache-Control'] = 'no-store'
        return {'version': corpus.version, 'institution': institution, 'limitations': corpus.limitations,
                'entries': [entry.model_dump() for entry in scoped_sources(corpus, institution)]}

    @router.post('/search')
    async def search_sources(body: SearchRequest, request: Request, response: Response):
        admit(request)
        _check_input(body.query)
        response.headers['Cache-Control'] = 'no-store'
        results, mode = await asyncio.to_thread(search_with_mode, _corpus(), body.query, body.limit,
                                                institution=body.institution)
        return {'query': body.query, 'institution': body.institution, 'retrieval_mode': mode, 'results': results}

    @router.post('/review')
    async def review_text(body: ReviewRequest, request: Request, response: Response):
        admit(request)
        _check_input(body.text, body.context)
        response.headers['Cache-Control'] = 'no-store'
        corpus = _corpus()
        if llm is not None:
            try:
                await asyncio.wait_for(model_slots.acquire(), timeout=0.1)
            except asyncio.TimeoutError as exc:
                raise HTTPException(429, 'Model review is busy; please try again.',
                                    headers={'Retry-After': '1'}) from exc
            try:
                address = client_ip(request.client.host if request.client else None,
                                    request.headers.get('x-forwarded-for'))
                try:
                    model_admission.reserve(address)
                except LimitExceeded as exc:
                    raise HTTPException(429, 'Model review limit reached; please try again later.',
                                        headers={'Retry-After': str(exc.retry_after)}) from exc
                return await agent_review(corpus, body.text, body.topics, body.context, llm, model, institution=body.institution)
            finally:
                model_slots.release()
        return await asyncio.to_thread(review, corpus, body.text, body.topics, body.context,
                                       institution=body.institution)

    @router.get('/gaps')
    async def candidate_gaps(request: Request, response: Response, scenario_id: str | None = None):
        admit(request)
        from .gaps import load_gaps
        response.headers['Cache-Control'] = 'no-store'
        try:
            return load_gaps(scenario_id)
        except ValueError as exc:
            raise HTTPException(404, 'Scenario not found') from exc

    def recording_from_bytes(data: bytes) -> dict:
        if len(data) > 1024 * 1024:
            raise HTTPException(413, 'Recording is too large')
        try:
            return validate_recording(json.loads(data))
        except (ValueError, TypeError, RecursionError, UnicodeError, AttributeError):
            raise HTTPException(422, 'Invalid recorded live exercise') from None

    @router.get('/replay')
    async def configured_replay(request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        path = os.environ.get('FRONTROW_POLICY_REPLAY_PATH')
        if not path:
            raise HTTPException(404, 'No recorded live exercise configured')
        try:
            with Path(path).open('rb') as source:
                data = source.read(1024 * 1024 + 1)
        except OSError:
            raise HTTPException(404, 'Recorded live exercise unavailable') from None
        return recording_from_bytes(data)

    @router.get('/replay/timeline.html')
    async def configured_replay_html(request: Request):
        replay = await configured_replay(request, Response())
        return Response(render_html(replay['recording']), media_type='text/html',
                        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename=yaplab-audit.html'})

    @router.post('/replays')
    async def import_replay(request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > 1024 * 1024:
                raise HTTPException(413, 'Recording is too large')
        recording = recording_from_bytes(bytes(chunks))
        if len(recordings) >= 50:
            raise HTTPException(429, 'Replay capacity reached')
        replay_id = secrets.token_urlsafe(24)
        recordings[replay_id] = recording
        return {'replay_id': replay_id, **recording}

    @router.get('/replays/{replay_id}')
    async def get_replay(replay_id: str, request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        if replay_id not in recordings:
            raise HTTPException(404, 'Replay not found')
        return {'replay_id': replay_id, **recordings[replay_id]}

    @router.get('/coordination/status')
    async def coordination_status(request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        return {'enabled': coordination_llm is not None,
                'review_mode': coordination_mode if coordination_llm is not None else 'offline_test',
                **({'model': role_model, 'provider': getattr(coordination_llm, 'provider_name', 'offline_test'),
                    'protocol_version': PROTOCOL_VERSION} if coordination_llm is not None else {})}

    @router.post('/exercises/{exercise_id}/coordinate')
    async def coordinate_exercise(exercise_id: str, body: CoordinationRequest,
                                  request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        store = _store(request)
        snapshot = store.reserve_coordination(exercise_id, body.expected_stage, body.institution,
                                              reuse_completed=True)
        if 'completed_result' in snapshot:
            return snapshot['completed_result']
        round_id = snapshot['round_id']
        try:
            if coordination_llm is None:
                raise HTTPException(503, 'No saved proposals exist and new model calls are not enabled.')
            address = client_ip(request.client.host if request.client else None,
                                request.headers.get('x-forwarded-for'))
            try:
                # Reserve all three calls atomically, shared with /review. Failed
                # or cancelled calls are not refunded: they may already be billed.
                if coordination_mode != 'offline_test':
                    model_admission.reserve(address, count=3)
            except LimitExceeded as exc:
                raise HTTPException(429, 'Policy model call limit reached; please try again later.',
                                    headers={'Retry-After': str(exc.retry_after)}) from exc
            result = await coordinate(_corpus(),
                {key: snapshot[key] for key in ('scenario_id', 'stage', 'role_views')},
                coordination_llm, role_model, institution=body.institution,
                mode=coordination_mode, shared_semaphore=model_slots)
            return store.commit_coordination(exercise_id, round_id, result)
        finally:
            store.release_coordination(exercise_id, round_id)

    @router.get('/exercises/{exercise_id}/coordination/{round_id}')
    async def get_coordination(exercise_id: str, round_id: str, request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        # This is an explicit facilitator view. IDs are capabilities, not login.
        return _store(request).get_coordination(exercise_id, round_id)

    return router
