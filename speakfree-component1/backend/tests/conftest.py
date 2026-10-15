"""
Test isolation: point the app at a throw-away SQLite database and static folder BEFORE any
backend module is imported, so tests can never touch backend/speakfree_c1.db or real images.
"""
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="speakfree-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/")
os.environ["STATIC_DIR"] = os.path.join(_TMP, "static")
os.environ["AUTO_MIGRATE"] = "false"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-0123456789"  # >= 32 bytes for HS256

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
