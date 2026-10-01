"""
Pytest fixtures — shared setup for all Python-based QA tools.

Usage:
    # In any test file:
    def test_api_health(api_client):
        assert api_client.health()

    def test_data_loads(sample_excel, tmp_path):
        assert len(sample_excel) > 0
"""

import os
import pytest
from core.base_api_client import BaseApiClient
from config.env import env


# ── Generic API client fixture ────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """Session-scoped API client pointed at QA_BASE_URL (or QA_API_BASE_URL)."""
    url = env.api_base_url or env.base_url
    if not url:
        pytest.skip("No QA_BASE_URL or QA_API_BASE_URL set — skipping API tests")
    return BaseApiClient(url, retries=2)


# ── Output directory fixture ─────────────────────────────────────────

@pytest.fixture
def output_dir(tmp_path):
    """Per-test temporary output directory."""
    d = tmp_path / "qa_output"
    d.mkdir()
    return d


# ── Reusable Excel loading fixture ───────────────────────────────────

@pytest.fixture
def load_excel():
    """Factory fixture: call with a path to load an Excel file as a DataFrame."""
    def _load(path, sheet_name=0):
        import pandas as pd
        return pd.read_excel(path, sheet_name=sheet_name)
    return _load


# ── Environment info fixture ─────────────────────────────────────────

@pytest.fixture(scope="session")
def qa_env():
    """Provides typed environment config to tests."""
    return env
