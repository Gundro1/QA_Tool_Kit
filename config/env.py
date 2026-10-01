"""
Centralized environment configuration.
Never read os.environ directly in scripts — import from here.

Usage:
    from config.env import env

    print(env.base_url)       # defaults to empty string if unset
    print(env.country_code)   # defaults to None
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Environment:
    """Typed, centralized access to environment variables."""

    # ── Web / API ─────────────────────────────────────────────────────
    base_url: str = field(
        default_factory=lambda: os.getenv("QA_BASE_URL", "")
    )
    api_base_url: str = field(
        default_factory=lambda: os.getenv("QA_API_BASE_URL", "")
    )

    # ── Defaults ──────────────────────────────────────────────────────
    country_code: Optional[str] = field(
        default_factory=lambda: os.getenv("QA_COUNTRY_CODE")
    )
    default_timeout_ms: int = field(
        default_factory=lambda: int(os.getenv("QA_TIMEOUT_MS", "30000"))
    )
    max_workers: int = field(
        default_factory=lambda: int(os.getenv("QA_MAX_WORKERS", "10"))
    )

    # ── Paths ─────────────────────────────────────────────────────────
    output_dir: str = field(
        default_factory=lambda: os.getenv("QA_OUTPUT_DIR", os.path.join(os.getcwd(), "reports"))
    )

    # ── Identity ──────────────────────────────────────────────────────
    auditor_name: str = field(
        default_factory=lambda: os.getenv("QA_AUDITOR", "QA Engineer")
    )

    # ── Flags ─────────────────────────────────────────────────────────
    verbose: bool = field(
        default_factory=lambda: os.getenv("QA_VERBOSE", "").lower() in ("1", "true", "yes")
    )
    ci: bool = field(
        default_factory=lambda: os.getenv("CI", "").lower() in ("1", "true", "yes")
    )


# Singleton — import this everywhere
env = Environment()
