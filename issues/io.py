from __future__ import annotations

import datetime
import json
import os
from typing import Iterable

from models.layer6 import Issue


def write_issues_json(issues: Iterable[Issue], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    issues = list(issues)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    for issue in issues:
        if issue.analysis_timestamp is None:
            issue.analysis_timestamp = timestamp

    payload = {
        "analysis_timestamp": timestamp,
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)