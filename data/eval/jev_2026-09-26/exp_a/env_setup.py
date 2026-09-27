"""Load OPENROUTER_API_KEY from the repo .env BEFORE any services.* import.
Import this module first, at the top of any script in this experiment."""
from dotenv import load_dotenv

REPO_ROOT = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
load_dotenv(REPO_ROOT + r"\.env")

import os
assert os.environ.get("OPENROUTER_API_KEY"), "OPENROUTER_API_KEY missing after load_dotenv"
