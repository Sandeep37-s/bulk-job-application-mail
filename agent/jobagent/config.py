import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

RESUME_PATH = ROOT / CFG["resume_path"]
DB_PATH = Path(os.getenv("JOBAGENT_DB", ROOT / "data" / "jobagent.db"))


def env(name, default=""):
    return os.getenv(name, default).strip()
