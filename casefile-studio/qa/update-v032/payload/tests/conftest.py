"""Isolated on-disk data for all API/production tests; never paid calls."""

import shutil
import uuid

import pytest
from fastapi.testclient import TestClient

import ai
import app as server
import renderer
import storage


@pytest.fixture
def isolated(monkeypatch):
    root = storage.ROOT / "qa" / ("test-" + uuid.uuid4().hex)
    data = root / "data"
    for sub in ["projects", "media", "jobs", "exports"]:
        (data / sub).mkdir(parents=True)
    for module in [server, storage, ai, renderer]:
        monkeypatch.setattr(module, "DATA", data)
    server.SESSIONS.clear()
    server.JOBS.clear()
    client = TestClient(server.app)
    yield client, root
    client.close()
    shutil.rmtree(root)
