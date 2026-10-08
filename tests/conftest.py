import os
import tempfile

# Set before any app module is imported, so tests never touch the real cache or spoken-reply files.
os.environ["CACHE_DIR"] = tempfile.mkdtemp(prefix="forward-check-tests-")
