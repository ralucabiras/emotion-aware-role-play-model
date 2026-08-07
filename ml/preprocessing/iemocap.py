"""Prepare licensed IEMOCAP metadata for speaker-independent experiments."""

import argparse
import hashlib
import json
import re
import tarfile
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath

ANNOTATION_RE = re.compile(
    r"^\[(?P<start>\d+(?:\.\d+)?)\s*-\s*(?P<end>\d+(?:\.\d+)?)\]\s+"
    r"(?P<utterance>Ses0[1-5][FM]_[^\s]+_[FM]\d+)\s+(?P<label>[a-z]{3})\s+"
    r"\[(?P<dimensions>[^]]+)\]"
)
TRANSCRIPT_RE = re.compile(r"^(?P<utterance>Ses0[1-5][FM]_.+_[FM]\d+)\s+\[[^]]+\]:\s*(?P<text>.*)$")
UTTERANCE_RE = re.compile(r"^Ses0(?P<session>[1-5])(?P<actor>[FM])_(?P<dialogue>.+)_(?P<speaker>[FM])\d+$")

TASKS = {
    "benchmark_4": {
        "labels": ["anger", "happiness", "neutral", "sadness"],
        "mapping": {"ang": "anger", "hap": "happiness", "exc": "happiness", "neu": "neutral", "sad": "sadness"},
        "description": "Conventional four-class benchmark; excitement is merged into happiness.",
    },
    "affectlab_6": {
        "labels": ["anger", "anxiety", "frustration", "joy", "neutral", "sadness"],
        "mapping": {
            "ang": "anger",
            "fea": "anxiety",
            "fru": "frustration",
            "hap": "joy",
            "exc": "joy",
            "neu": "neutral",
            "sad": "sadness",
        },
        "description": "Application-aligned labels; frustration and fear/anxiety remain distinct.",
    },
}


def _is_metadata_member(name: str) -> bool:
    raw_path = PurePosixPath(name)
    if raw_path.is_absolute() or ".." in raw_path.parts:
        return False
    parts = tuple(part for part in raw_path.parts if part not in {".", ""})
    path = PurePosixPath(*parts)
    if path.name.startswith("._"):
        return False
    return path.suffix == ".txt" and (
        "dialog/EmoEvaluation" in path.as_posix() or "dialog/transcriptions" in path.as_posix()
    )


def extract_metadata(archive: Path, destination: Path) -> Path:
    """Extract only annotation/transcript text, never the licensed media payload."""
    destination.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with tarfile.open(archive, mode="r:gz") as bundle:
        for member in bundle:
            if not member.isfile() or not _is_metadata_member(member.name):
                continue
            relative = PurePosixPath(*(part for part in PurePosixPath(member.name).parts if part not in {".", ""}))
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read archive member: {member.name}")
            with target.open("wb") as handle:
                while chunk := source.read(1024 * 1024):
                    handle.write(chunk)
            extracted += 1
    if not extracted:
        raise ValueError("No IEMOCAP annotation or transcription files found in archive")
    return locate_release_root(destination)


def locate_release_root(path: Path) -> Path:
    direct = path / "IEMOCAP_full_release"
    if direct.is_dir():
        return direct
    if all((path / f"Session{session}").is_dir() for session in range(1, 6)):
        return path
    matches = list(path.glob("**/IEMOCAP_full_release"))
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"Could not locate IEMOCAP_full_release under {path}")


def parse_transcript_line(line: str) -> tuple[str, str] | None:
    match = TRANSCRIPT_RE.match(line.strip())
    if not match:
        return None
    return match["utterance"], match["text"].strip()


def parse_annotation_line(line: str) -> dict | None:
    match = ANNOTATION_RE.match(line.strip())
    if not match:
        return None
    identity = UTTERANCE_RE.match(match["utterance"])
    if not identity:
        raise ValueError(f"Unrecognized IEMOCAP utterance id: {match['utterance']}")
    dimensions = [float(value.strip()) for value in match["dimensions"].split(",")]
    if len(dimensions) != 3:
        raise ValueError(f"Expected valence/arousal/dominance values: {line.strip()}")
    dialogue_id = match["utterance"].rsplit("_", 1)[0]
    return {
        "id": match["utterance"],
        "session": int(identity["session"]),
        "speaker": f"Ses0{identity['session']}{identity['speaker']}",
        "dialogue_id": dialogue_id,
        "is_improvised": "_impro" in dialogue_id,
        "start_seconds": float(match["start"]),
        "end_seconds": float(match["end"]),
        "source_label": match["label"],
        "valence": dimensions[0],
        "arousal": dimensions[1],
        "dominance": dimensions[2],
        "audio_archive_member": (
            f"IEMOCAP_full_release/Session{identity['session']}/sentences/wav/"
            f"{dialogue_id}/{match['utterance']}.wav"
        ),
    }


def load_records(release_root: Path) -> list[dict]:
    transcripts = {}
    for path in sorted(release_root.glob("Session*/dialog/transcriptions/*.txt")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse_transcript_line(line)
            if parsed:
                utterance_id, text = parsed
                transcripts[utterance_id] = text

    records = []
    seen = set()
    for path in sorted(release_root.glob("Session*/dialog/EmoEvaluation/*.txt")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            record = parse_annotation_line(line)
            if record is None:
                continue
            if record["id"] in seen:
                raise ValueError(f"Duplicate categorical annotation: {record['id']}")
            seen.add(record["id"])
            text = transcripts.get(record["id"], "").strip()
            if not text:
                raise ValueError(f"Missing transcript for {record['id']}")
            record["text"] = text
            records.append(record)
    if not records:
        raise ValueError("No categorical IEMOCAP annotations were parsed")
    return records


def add_context_fields(records: list[dict], context_turns: int = 3) -> list[dict]:
    """Add causal dialogue context without using future utterances or labels."""
    if context_turns < 0:
        raise ValueError("context_turns must be non-negative")
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["dialogue_id"], []).append(record)
    enriched = []
    for dialogue in grouped.values():
        ordered = sorted(dialogue, key=lambda row: (row["start_seconds"], row["id"]))
        for index, record in enumerate(ordered):
            previous = ordered[max(0, index - context_turns) : index]
            segments = [
                f"[{'same speaker' if turn['speaker'] == record['speaker'] else 'other speaker'}] {turn['text']}"
                for turn in previous
            ]
            segments.append(f"[target] {record['text']}")
            enriched.append(
                {
                    **record,
                    "context_text": "\n".join(segments),
                    "context_turn_count": len(previous),
                }
            )
    return sorted(enriched, key=lambda row: row["id"])


def fold_sessions(test_session: int) -> dict[str, list[int]]:
    if test_session not in range(1, 6):
        raise ValueError("test_session must be between 1 and 5")
    validation_session = 5 if test_session == 1 else test_session - 1
    train_sessions = sorted(set(range(1, 6)) - {test_session, validation_session})
    return {"train": train_sessions, "validation": [validation_session], "test": [test_session]}


def prepare(release_root: Path, output_dir: Path, archive_metadata: dict | None = None) -> dict:
    from datasets import Dataset, DatasetDict

    records = add_context_fields(load_records(locate_release_root(release_root)))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset": "IEMOCAP",
        "release": "IEMOCAP_full_release",
        "license": "Access-controlled; no redistribution of raw or derived row-level data.",
        "archive": archive_metadata or {},
        "context": {
            "field": "context_text",
            "previous_turns": 3,
            "causal": True,
            "speaker_markers": ["same speaker", "other speaker", "target"],
        },
        "source_label_counts": dict(sorted(Counter(row["source_label"] for row in records).items())),
        "tasks": {},
    }
    for task_name, task in TASKS.items():
        labels = task["labels"]
        mapped = []
        for record in records:
            label_name = task["mapping"].get(record["source_label"])
            if label_name is None:
                continue
            mapped.append({**record, "label_name": label_name, "label": labels.index(label_name)})
        task_manifest = {"labels": labels, "mapping": task["mapping"], "description": task["description"], "folds": {}}
        for test_session in range(1, 6):
            sessions = fold_sessions(test_session)
            split_rows = {
                split: [row for row in mapped if row["session"] in split_sessions]
                for split, split_sessions in sessions.items()
            }
            speakers = {split: {row["speaker"] for row in rows} for split, rows in split_rows.items()}
            if any(speakers[left] & speakers[right] for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))):
                raise ValueError(f"Speaker leakage in {task_name} fold {test_session}")
            dataset = DatasetDict({split: Dataset.from_list(rows) for split, rows in split_rows.items()})
            fold_dir = output_dir / task_name / f"fold-{test_session}"
            dataset.save_to_disk(str(fold_dir / "dataset"))
            task_manifest["folds"][str(test_session)] = {
                "sessions": sessions,
                "examples": {split: len(rows) for split, rows in split_rows.items()},
                "speakers": {split: sorted(values) for split, values in speakers.items()},
                "label_counts": {
                    split: dict(sorted(Counter(row["label_name"] for row in rows).items()))
                    for split, rows in split_rows.items()
                },
            }
        manifest["tasks"][task_name] = task_manifest
    encoded = json.dumps(manifest, sort_keys=True).encode()
    manifest["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--release-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--archive-generation")
    args = parser.parse_args()
    archive_details = {
        key: value
        for key, value in {
            "filename": args.archive.name if args.archive else None,
            "sha256": args.archive_sha256,
            "gcs_generation": args.archive_generation,
        }.items()
        if value is not None
    }
    if args.archive:
        with tempfile.TemporaryDirectory(prefix="iemocap-metadata-") as temporary:
            root = extract_metadata(args.archive, Path(temporary))
            result = prepare(root, args.output_dir, archive_details)
    else:
        result = prepare(args.release_root, args.output_dir, archive_details)
    print(json.dumps(result, indent=2))
