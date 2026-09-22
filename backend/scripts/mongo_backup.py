"""BSON-preserving MongoDB backup and restore verification for AffectLab."""
import argparse
import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from bson import BSON, decode_all
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from pymongo import MongoClient

UUID_CODEC = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)


def backup_database(uri: str, database: str, destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=False)
    client = MongoClient(uri, uuidRepresentation="standard")
    db = client[database]
    manifest = {"schema_version": "affectlab-mongodb-backup-v1", "database": database, "created_at": datetime.now(UTC).isoformat(), "collections": {}}
    try:
        for name in sorted(item for item in db.list_collection_names() if not item.startswith("system.")):
            payload = b"".join(
                BSON.encode(document, codec_options=UUID_CODEC) for document in db[name].find({})
            )
            archive = destination / f"{name}.bson.gz"
            with gzip.open(archive, "wb") as stream:
                stream.write(payload)
            indexes = []
            for index_name, specification in db[name].index_information().items():
                if index_name == "_id_":
                    continue
                indexes.append({
                    "name": index_name,
                    "keys": specification["key"],
                    "unique": specification.get("unique", False),
                    "expireAfterSeconds": specification.get("expireAfterSeconds"),
                })
            manifest["collections"][name] = {
                "documents": db[name].count_documents({}),
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "indexes": indexes,
            }
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    finally:
        client.close()


def restore_database(uri: str, source: Path, target_database: str, *, allow_non_test_target: bool = False) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if target_database == manifest["database"]:
        raise ValueError("Restore target must differ from the source database")
    if not allow_non_test_target and not target_database.endswith("_restore_test"):
        raise ValueError("Restore target must end with _restore_test unless explicitly overridden")
    client = MongoClient(uri, uuidRepresentation="standard")
    target = client[target_database]
    try:
        if target.list_collection_names():
            raise ValueError("Restore target database must be empty")
        restored = {}
        for name, expected in manifest["collections"].items():
            archive = source / f"{name}.bson.gz"
            if hashlib.sha256(archive.read_bytes()).hexdigest() != expected["sha256"]:
                raise ValueError(f"Checksum mismatch for {name}")
            with gzip.open(archive, "rb") as stream:
                documents = decode_all(stream.read(), codec_options=UUID_CODEC)
            if documents:
                target[name].insert_many(documents)
            for index in expected.get("indexes", []):
                options = {"name": index["name"], "unique": index["unique"]}
                if index.get("expireAfterSeconds") is not None:
                    options["expireAfterSeconds"] = index["expireAfterSeconds"]
                target[name].create_index([tuple(key) for key in index["keys"]], **options)
            actual = target[name].count_documents({})
            if actual != expected["documents"]:
                raise ValueError(f"Document-count mismatch for {name}: expected {expected['documents']}, restored {actual}")
            restored[name] = actual
        return {"target_database": target_database, "collections": restored, "verified": True}
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    backup = subcommands.add_parser("backup")
    backup.add_argument("--uri", required=True)
    backup.add_argument("--database", required=True)
    backup.add_argument("--destination", type=Path, required=True)
    restore = subcommands.add_parser("restore-test")
    restore.add_argument("--uri", required=True)
    restore.add_argument("--source", type=Path, required=True)
    restore.add_argument("--target-database", required=True)
    args = parser.parse_args()
    result = backup_database(args.uri, args.database, args.destination) if args.command == "backup" else restore_database(args.uri, args.source, args.target_database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
