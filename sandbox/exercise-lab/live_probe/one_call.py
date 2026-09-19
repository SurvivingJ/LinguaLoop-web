"""Smallest possible script: ONE real OpenRouter call, timed. Run this first."""
import os, sys, time, json, hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]  # WebApp/
sys.path.insert(0, str(ROOT / "sandbox" / "exercise-lab" / "prototypes" / "fat_seed"))

# load .env manually (no external dep needed)
env_path = ROOT / ".env"
env = {}
for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")

API_KEY = env.get("OPENROUTER_API_KEY")
if not API_KEY:
    print("NO KEY FOUND"); sys.exit(1)

from prompt_builder import build_fat_seed_prompt

import requests

prompt = build_fat_seed_prompt("跑", 1, pos_hint="verb")  # zh, "run"

t0 = time.time()
resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": "google/gemini-3.5-flash-lite",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    },
    timeout=120,
)
elapsed = time.time() - t0

print("STATUS:", resp.status_code)
print("ELAPSED_SEC:", round(elapsed, 2))
if resp.status_code != 200:
    print("BODY:", resp.text[:2000])
    sys.exit(1)

data = resp.json()
usage = data.get("usage", {})
print("USAGE:", usage)
content = data["choices"][0]["message"]["content"]
print("CONTENT_LEN:", len(content))

# cache raw response FIRST (before any risky console printing)
cache_dir = ROOT / "sandbox" / "exercise-lab" / "fixtures" / "live_responses"
cache_dir.mkdir(parents=True, exist_ok=True)
h = hashlib.sha256(prompt.encode()).hexdigest()[:16]
out_path = cache_dir / f"gemini-3.5-flash-lite_zh_fat_{h}.json"
out_path.write_text(json.dumps({"prompt": prompt, "elapsed_sec": elapsed, "response": data}, ensure_ascii=False, indent=2), encoding="utf-8")
print("CACHED:", out_path)
print("CONTENT_HEAD:", content[:300].encode("ascii", "replace").decode("ascii"))
