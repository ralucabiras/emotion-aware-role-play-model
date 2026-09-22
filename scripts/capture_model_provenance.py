"""Capture immutable hashes and environment metadata for private final model artifacts."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_manifest(path: Path) -> dict:
    if not path.is_dir():
        raise ValueError(f"Model directory does not exist: {path}")
    files = [item for item in sorted(path.rglob("*")) if item.is_file()]
    entries = [{"path": item.relative_to(path).as_posix(), "bytes": item.stat().st_size, "sha256": sha256(item)} for item in files]
    aggregate = hashlib.sha256("\n".join(f"{item['sha256']}  {item['path']}" for item in entries).encode()).hexdigest()
    return {"directory_name": path.name, "files": entries, "aggregate_sha256": aggregate}


def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-model", type=Path, required=True)
    parser.add_argument("--audio-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    config = ROOT / "configs" / "iemocap_final_multimodal.json"
    result = {
        "schema_version": "affectlab-model-provenance-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "configuration": {"path": config.relative_to(ROOT).as_posix(), "sha256": sha256(config)},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": version("torch"),
            "transformers": version("transformers"),
            "pymongo": version("pymongo"),
            "openai": version("openai"),
        },
        "text_model": directory_manifest(args.text_model.resolve()),
        "audio_model": directory_manifest(args.audio_model.resolve()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote provenance for {len(result['text_model']['files']) + len(result['audio_model']['files'])} files to {args.output}")


if __name__ == "__main__":
    main()
