"""Evidence endpoints and explicitly enabled synthetic coordination rounds."""
from __future__ import annotations

import asyncio
import math
import re
import time
from collections import deque
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from frontrow.limits import DemoLimits, LimitExceeded, client_ip
from frontrow.llm.base import LLMClient
from .agent import agent_review
from .coordination import coordinate, Mode
from .scenarios import _store
from .evidence import CorpusUnavailable, Institution, Topic, load_corpus, scoped_sources, search
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

    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._monotonic = monotonic
        self._hourly = DemoLimits(sessions_per_ip_per_hour=8, max_sessions_per_day=100,
                                  monotonic=monotonic)
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
        if entries and len(entries) + count > 20:
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
    model_admission = ModelCallLimits()
    model_slots = asyncio.Semaphore(2)

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
        return {'query': body.query, 'institution': body.institution, 'results': search(_corpus(), body.query, body.limit, institution=body.institution)}

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
        return review(corpus, body.text, body.topics, body.context, institution=body.institution)

    @router.get('/coordination/status')
    async def coordination_status(request: Request, response: Response):
        admit(request)
        response.headers['Cache-Control'] = 'no-store'
        return {'enabled': coordination_llm is not None,
                'review_mode': coordination_mode if coordination_llm is not None else 'offline_test',
                **({'model': role_model} if coordination_llm is not None else {})}

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
