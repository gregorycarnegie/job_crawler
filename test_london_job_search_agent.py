"""Test‑suite for main.py (pytest).

These tests run **entirely offline** by monkey‑patching `httpx.AsyncClient` so
we never hit the real Adzuna API.  They are mainly smoke / contract tests to
ensure that:

1. The tool returns a list of dicts with the expected keys.
2. `max_results` is respected.
3. Environment variables are required (but can be faked during the test).

Run with:
```
pip install pytest
pytest -q
```
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Fixture: monkey‑patch Async HTTP layer
# ---------------------------------------------------------------------------

_SAMPLE_API_PAYLOAD: Dict[str, Any] = {
    "results": [
        {
            "title": "Senior Python Engineer",
            "company": {"display_name": "Acme Corp"},
            "location": {"display_name": "London"},
            "salary_min": 70000,
            "salary_max": 90000,
            "contract_type": "full_time",
            "redirect_url": "https://example.com/job/123",
            "description": "Work on cutting‑edge fintech systems in the heart of London.",
        },
    ]
}


class _DummyResponse:
    """Mimics the interface of `httpx.Response` used in the code."""

    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:  # noqa: D401
        return None  # Always OK

    def json(self) -> Dict[str, Any]:  # noqa: D401
        return self._payload


class _DummyAsyncClient:
    """Pretends to be `httpx.AsyncClient`, but never touches the network."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        pass

    async def __aenter__(self) -> "_DummyAsyncClient":  # noqa: D401
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:  # noqa: D401
        return None

    async def get(self, endpoint: str, params: Dict[str, Any] | None = None) -> _DummyResponse:  # noqa: D401,E501
        # For testing, we ignore *endpoint* and *params* completely.
        return _DummyResponse(_SAMPLE_API_PAYLOAD)


# ---------------------------------------------------------------------------
# The actual tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_env_and_httpx(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    """Provide fake env vars + swap out `httpx.AsyncClient`."""

    # 1) Ensure credentials look present so the code doesn’t bail out early
    monkeypatch.setenv("ADZUNA_APP_ID", "dummy_id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "dummy_key")

    # 2) Monkey‑patch httpx.AsyncClient in the *module under test* ONLY.
    import importlib

    agent = importlib.import_module("main")
    monkeypatch.setattr(agent.httpx, "AsyncClient", _DummyAsyncClient)


@pytest.mark.asyncio
async def test_returns_expected_schema() -> None:  # noqa: D401
    """Basic smoke test — correct keys & type."""

    from main import search_london_jobs

    jobs = await search_london_jobs("python", max_results=10)

    assert isinstance(jobs, list)
    assert len(jobs) == 1  # our dummy payload contains 1 listing

    first = jobs[0]
    assert set(first.keys()) == {
        "title",
        "company",
        "location",
        "salary_min",
        "salary_max",
        "contract_type",
        "url",
        "description",
    }
    assert first["title"] == "Senior Python Engineer"


@pytest.mark.asyncio
async def test_respects_max_results_parameter() -> None:  # noqa: D401
    """Even if the API returns more entries, the function must cap output."""

    from main import search_london_jobs

    # Our dummy API payload always holds 1 result.  Ask for 1 & expect 1.
    jobs = await search_london_jobs("python", max_results=1)
    assert len(jobs) == 1


def test_env_vars_required(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    """If creds are missing, code should raise RuntimeError."""

    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)

    from main import search_london_jobs

    with pytest.raises(RuntimeError):
        # Use sync wrapper to call async fn in a test that expects an exception.
        asyncio.run(search_london_jobs("java"))
