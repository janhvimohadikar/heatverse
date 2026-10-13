"""Checks that no secrets are present in files that would be committed to GitHub."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", ".pytest_cache"}
SKIP_SUFFIX = {".db", ".xlsx", ".png", ".jpg", ".ico", ".zip", ".pyc", ".geojson"}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "OpenAI/Anthropic style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
}


def _files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.suffix not in SKIP_SUFFIX:
            yield p


def test_no_secret_patterns():
    hits = []
    for p in _files():
        if p.name == "test_repo_hygiene.py":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, rx in PATTERNS.items():
            if rx.search(text):
                hits.append(f"{p.relative_to(ROOT)}: {name}")
    assert not hits, hits


def test_real_env_files_are_not_in_the_repo_tree():
    leaked = [str(p.relative_to(ROOT)) for p in _files() if p.name == ".env"]
    assert not leaked, f"Remove real .env files before committing: {leaked}"


def test_env_examples_have_placeholders_only():
    for p in ROOT.rglob(".env.example"):
        if set(p.parts) & SKIP_DIRS:
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("SECRET_KEY="):
                assert line.split("=", 1)[1].startswith("change-me"), p
