"""Central configuration for the Flask backend."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

DB_DIR = os.path.join(ROOT_DIR, "database")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(DB_DIR, "irrigation.db"))
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")

STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(ROOT_DIR, "uploads"))              # raw uploaded files
USER_MODEL_DIR = os.environ.get("USER_MODEL_DIR", os.path.join(ROOT_DIR, "user_models"))  # SVMs trained on uploads
MAX_UPLOAD_MB = 25
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
