import asyncio

import pytest


# Provide an asyncio event loop for tests that use asyncio
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class DummyCache:
    """A minimal in-memory cache compatible with a handful of project helpers.

    Only implements the methods used in unit tests and fixtures.
    """

    def __init__(self):
        self._store: dict = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, ttl=None):
        self._store[key] = value

    # live matches helpers used by some use-cases
    def get_live_matches(self, key):
        return self._store.get(f"live::{key}")

    def set_live_matches(self, value, key):
        self._store[f"live::{key}"] = value


@pytest.fixture
def dummy_cache():
    return DummyCache()
