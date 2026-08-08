import io
import tarfile
import wave

from datasets import Dataset, DatasetDict
from ml.preprocessing.iemocap_audio import build_bundle, normalized_member_name


def wav_bytes(sample_rate: int = 16_000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * 160)
    return output.getvalue()


def test_audio_member_normalization_rejects_traversal() -> None:
    assert normalized_member_name("./IEMOCAP_full_release/file.wav") == "IEMOCAP_full_release/file.wav"
    try:
        normalized_member_name("../../outside.wav")
    except ValueError:
        pass
    else:
        raise AssertionError("Path traversal was accepted")


def test_iemocap_audio_bundle_is_task_specific_and_audited(tmp_path) -> None:
    member_name = "IEMOCAP_full_release/Session1/sentences/wav/d/u.wav"
    row = {"id": "u", "audio_archive_member": member_name}
    dataset = DatasetDict({split: Dataset.from_list([row]) for split in ("train", "validation", "test")})
    dataset_dir = tmp_path / "dataset"
    dataset.save_to_disk(str(dataset_dir))
    archive = tmp_path / "source.tar.gz"
    payload = wav_bytes()
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo(f"./{member_name}")
        member.size = len(payload)
        bundle.addfile(member, io.BytesIO(payload))

    output = tmp_path / "audio.tar.gz"
    manifest = build_bundle(archive, dataset_dir, output, "abc")

    assert manifest["files"] == 1
    assert manifest["sample_rate_counts"] == {"16000": 1}
    assert manifest["source_archive_sha256"] == "ABC"
    with tarfile.open(output, "r:gz") as bundle:
        assert bundle.getnames() == ["audio/u.wav"]
