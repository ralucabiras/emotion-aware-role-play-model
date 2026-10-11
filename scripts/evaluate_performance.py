"""Reproducible local latency check for AffectLab's deterministic core workflow.

This is a single-client engineering benchmark using FastAPI's in-process test
transport and the memory repository. It includes routing, authentication,
validation, application services, and response serialisation, but excludes a
network hop, MongoDB, external providers, and trained multimodal inference.
It is therefore a regression check, not a deployment-capacity claim.
"""

import asyncio
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

os.environ["PERSISTENCE_BACKEND"] = "memory"
os.environ["SMTP_HOST"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["TRANSCRIPTION_ENABLED"] = "false"
os.environ["MULTIMODAL_INFERENCE_ENABLED"] = "false"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.container import auth_service, repository  # noqa: E402
from app.main import app  # noqa: E402
from app.models.domain import User, utcnow  # noqa: E402

P95_BUDGET_MS = {
    "liveness": 25.0,
    "scenario_catalogue": 50.0,
    "session_create": 50.0,
    "roleplay_start": 75.0,
    "deterministic_chat_turn": 100.0,
}


def percentile(samples: list[float], probability: float) -> float:
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def summary(samples: list[float]) -> dict[str, float | int]:
    return {
        "n": len(samples),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(percentile(samples, 0.95), 3),
        "max_ms": round(max(samples), 3),
    }


def timed_request(client: TestClient, method: str, path: str, **kwargs):
    started = time.perf_counter()
    response = client.request(method, path, **kwargs)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return response, elapsed_ms


def main() -> int:
    user = User(
        email="performance-check@example.com",
        password_hash="not-used-by-performance-check",
        consented_at=utcnow(),
        email_verified_at=utcnow(),
    )

    results: dict[str, list[float]] = {
        "liveness": [],
        "scenario_catalogue": [],
        "session_create": [],
        "roleplay_start": [],
        "deterministic_chat_turn": [],
    }

    with TestClient(app) as client:
        asyncio.run(repository.create_user(user))
        headers = {"Authorization": f"Bearer {auth_service.access_token(user.id)}"}

        # Warm routing, schema, and service paths before collecting samples.
        client.get("/api/health/live")
        client.get("/api/roleplay/scenarios", headers=headers)

        for _ in range(200):
            _, elapsed = timed_request(client, "GET", "/api/health/live")
            results["liveness"].append(elapsed)
            _, elapsed = timed_request(
                client, "GET", "/api/roleplay/scenarios", headers=headers
            )
            results["scenario_catalogue"].append(elapsed)

        for _ in range(100):
            response, elapsed = timed_request(
                client, "POST", "/api/sessions", headers=headers
            )
            results["session_create"].append(elapsed)
            session_id = response.json()["session_id"]

            response, elapsed = timed_request(
                client,
                "POST",
                f"/api/sessions/{session_id}/roleplay",
                headers=headers,
                json={
                    "scenario_id": "workload",
                    "difficulty": "intermediate",
                    "pre_skipped": True,
                },
            )
            results["roleplay_start"].append(elapsed)

            response, elapsed = timed_request(
                client,
                "POST",
                "/api/chat",
                headers=headers,
                json={
                    "request_id": str(uuid4()),
                    "session_id": session_id,
                    "message": (
                        "I have too many tasks and twelve hours of work. "
                        "Could you help me prioritise?"
                    ),
                    "expected_version": response.json()["version"],
                },
            )
            results["deterministic_chat_turn"].append(elapsed)

    source_paths = [
        "backend/app/main.py",
        "backend/app/api/routes.py",
        "backend/app/services/conversation_service.py",
        "backend/app/services/roleplay_service.py",
        "backend/app/repositories/memory.py",
        "scripts/evaluate_performance.py",
    ]
    summaries = {name: summary(samples) for name, samples in results.items()}
    checks = {
        name: {
            "p95_budget_ms": budget,
            "passed": summaries[name]["p95_ms"] <= budget,
        }
        for name, budget in P95_BUDGET_MS.items()
    }
    report = {
        "version": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "scope": (
            "single-client in-process HTTP benchmark with MemoryRepository and "
            "deterministic fallbacks; excludes network, MongoDB, external providers, "
            "trained inference, and concurrent load"
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in source_paths
        },
        "results": summaries,
        "regression_checks": checks,
    }
    output = ROOT / "docs/evidence-package/generated/performance-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all(check["passed"] for check in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
