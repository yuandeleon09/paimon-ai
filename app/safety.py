import re
from pathlib import Path

# Common patterns for API keys and sensitive tokens
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{30,45}"),            # Google API key
    re.compile(r"sk-[a-zA-Z0-9]{32,70}"),                # OpenAI / Anthropic format
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),       # GitHub tokens
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]"),
]

def sanitize_text(text: str, mask: str = "[REDACTED_SECRET]") -> str:
    """Removes sensitive keys, passwords, and tokens from any text."""
    if not text:
        return text

    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(mask, sanitized)
    return sanitized

def contains_secret(text: str) -> bool:
    """Returns True if any sensitive token pattern is detected."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)

def validate_safe_path(target_path: Path, base_dir: Path) -> bool:
    """Ensures a path cannot escape the designated base directory (prevents path traversal)."""
    try:
        resolved_target = target_path.resolve()
        resolved_base = base_dir.resolve()
        return resolved_base in resolved_target.parents or resolved_target == resolved_base
    except Exception:
        return False
