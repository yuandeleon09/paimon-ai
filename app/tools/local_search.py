from pathlib import Path
from typing import List, Dict, Any

def search_text_files(base_dir: Path, keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """Deterministically searches markdown and text files within base_dir for given keywords."""
    results = []
    if not base_dir.exists():
        return results

    normalized_keywords = [k.lower().strip() for k in keywords if k.strip()]
    if not normalized_keywords:
        return results

    for file_path in base_dir.rglob("*.md"):
        # Ignore runs to avoid mixing unverified history into raw searches
        if "03_Runs" in file_path.parts:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            matched_lines = []
            score = 0

            for idx, line in enumerate(lines, start=1):
                line_lower = line.lower()
                matches = [k for k in normalized_keywords if k in line_lower]
                if matches:
                    score += len(matches)
                    matched_lines.append((idx, line.strip()))

            if score > 0:
                rel_path = file_path.relative_to(base_dir).as_posix()
                results.append({
                    "path": rel_path,
                    "score": score,
                    "matched_lines": matched_lines[:5],
                    "total_matches": len(matched_lines)
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
