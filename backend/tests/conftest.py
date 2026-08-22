import os

# Unit and API tests must not depend on a developer's local MongoDB or SMTP
# configuration. Mongo persistence is covered separately at the repository
# integration boundary.
os.environ["PERSISTENCE_BACKEND"] = "memory"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_SENDER"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["TRANSCRIPTION_ENABLED"] = "false"
os.environ["MULTIMODAL_INFERENCE_ENABLED"] = "false"
