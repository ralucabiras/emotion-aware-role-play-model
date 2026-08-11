from bson.binary import UuidRepresentation

from app.repositories.mongo import MongoRepository


def test_mongo_repository_uses_standard_uuid_representation() -> None:
    repository = MongoRepository("mongodb://localhost:27017", "affectlab-test")

    assert repository.db.codec_options.uuid_representation == UuidRepresentation.STANDARD
