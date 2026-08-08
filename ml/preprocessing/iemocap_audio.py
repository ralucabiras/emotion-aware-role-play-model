"""Build a private, task-specific IEMOCAP sentence-audio bundle."""

import argparse
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import wave
from collections import Counter
from pathlib import Path, PurePosixPath


def normalized_member_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive member: {name}")
    return PurePosixPath(*(part for part in path.parts if part not in {".", ""})).as_posix()


def target_members(dataset_dir: Path) -> dict[str, str]:
    from datasets import load_from_disk

    dataset = load_from_disk(str(dataset_dir))
    targets = {}
    for split in ("train", "validation", "test"):
        for row in dataset[split]:
            member = row["audio_archive_member"]
            existing = targets.setdefault(member, row["id"])
            if existing != row["id"]:
                raise ValueError(f"Audio member maps to multiple ids: {member}")
    return targets


def build_bundle(archive: Path, dataset_dir: Path, output: Path, source_sha256: str) -> dict:
    targets = target_members(dataset_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_rates: Counter[int] = Counter()
    channels: Counter[int] = Counter()
    sample_widths: Counter[int] = Counter()
    durations = []
    total_pcm_bytes = 0
    found = set()
    with tarfile.open(archive, "r:gz") as source_bundle, tarfile.open(output, "w:gz", compresslevel=6) as output_bundle:
        for member in source_bundle:
            if not member.isfile():
                continue
            name = normalized_member_name(member.name)
            utterance_id = targets.get(name)
            if utterance_id is None:
                continue
            source = source_bundle.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read {name}")
            with tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024) as temporary:
                shutil.copyfileobj(source, temporary, length=1024 * 1024)
                temporary.seek(0)
                with wave.open(temporary, "rb") as audio:
                    rate = audio.getframerate()
                    frame_count = audio.getnframes()
                    channel_count = audio.getnchannels()
                    sample_width = audio.getsampwidth()
                sample_rates[rate] += 1
                channels[channel_count] += 1
                sample_widths[sample_width] += 1
                durations.append(frame_count / rate)
                total_pcm_bytes += frame_count * channel_count * sample_width
                temporary.seek(0, io.SEEK_END)
                size = temporary.tell()
                temporary.seek(0)
                target = tarfile.TarInfo(f"audio/{utterance_id}.wav")
                target.size = size
                target.mode = 0o600
                target.mtime = 0
                output_bundle.addfile(target, temporary)
            found.add(name)
    missing = sorted(targets.keys() - found)
    if missing:
        output.unlink(missing_ok=True)
        raise ValueError(f"Missing {len(missing)} target WAV files; first: {missing[:3]}")
    digest = hashlib.sha256()
    with output.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    manifest = {
        "dataset": "IEMOCAP",
        "task": "benchmark_4",
        "files": len(found),
        "bundle_filename": output.name,
        "bundle_bytes": output.stat().st_size,
        "bundle_sha256": digest.hexdigest().upper(),
        "source_archive_sha256": source_sha256.upper(),
        "sample_rate_counts": {str(key): value for key, value in sorted(sample_rates.items())},
        "channel_counts": {str(key): value for key, value in sorted(channels.items())},
        "sample_width_byte_counts": {str(key): value for key, value in sorted(sample_widths.items())},
        "duration_seconds": {
            "total": sum(durations),
            "minimum": min(durations),
            "maximum": max(durations),
            "mean": sum(durations) / len(durations),
        },
        "uncompressed_pcm_bytes": total_pcm_bytes,
        "archive_layout": "audio/{utterance_id}.wav",
    }
    output.with_suffix(output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def extract_bundle(bundle: Path, destination: Path, expected_files: int) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with tarfile.open(bundle, "r:gz") as archive:
        for member in archive:
            name = normalized_member_name(member.name)
            path = PurePosixPath(name)
            if not member.isfile() or len(path.parts) != 2 or path.parts[0] != "audio" or path.suffix != ".wav":
                raise ValueError(f"Unexpected audio bundle member: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read audio bundle member: {member.name}")
            target = destination / path.parts[0] / path.parts[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                shutil.copyfileobj(source, handle, length=1024 * 1024)
            extracted += 1
    if extracted != expected_files:
        raise ValueError(f"Expected {expected_files} audio files, extracted {extracted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(build_bundle(args.archive, args.dataset_dir, args.output, args.source_sha256), indent=2))
