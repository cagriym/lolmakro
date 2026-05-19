from __future__ import annotations

from pathlib import Path
import os
import sys

from dotenv import load_dotenv

from desktop_bridge import run


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    load_dotenv()
    load_dotenv(Path(os.environ.get("LOCALAPPDATA", ".")) / "LolMakroBridge" / ".env")
    run()
