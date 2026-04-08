"""
sec-quest/server/grader.py

Deterministic grader that scores an agent's review comments
against the ground-truth bug manifest.

Scoring per bug found:
  +0.30  correctly identified (line within ±3 of bug line)
  +0.10  correct category label
  +0.10  correct severity label
  ------------
  +0.50  max per bug

False positive penalty:
  -0.15  per comment that doesn't map to any planted bug

Completion bonus:
  +0.20  if all bugs are found before calling 'done' / 'request_changes'

Approve-with-bugs penalty:
  -0.50  if agent calls 'approve' and critical bugs remain unfound

Final score is normalized to (0.0, 1.0) - strictly between 0 and 1.
"""

from typing import List, Dict, Any


LINE_TOLERANCE = 3   # ±3 lines counts as "correct line"

# Score must be strictly between 0 and 1 (not exactly 0.0 or 1.0)
EPSILON = 0.001
MIN_SCORE = EPSILON
MAX_SCORE = 1.0 - EPSILON

CATEGORY_SCORES = {
    "security": 0.10,
    "logic": 0.10,
    "race_condition": 0.10,
    "performance": 0.10,
    "style": 0.05,
}

SEVERITY_SCORES = {
    "critical": 0.10,
    "major": 0.08,
    "minor": 0.05,
}


def _line_matches(comment_line: int, bug: Dict[str, Any]) -> bool:
    """Return True if the comment's line is within LINE_TOLERANCE of the bug's line range."""
    lo, hi = bug["line_range"]
    return (lo - LINE_TOLERANCE) <= comment_line <= (hi + LINE_TOLERANCE)


def grade(
    comments: List[Dict[str, Any]],
    bug_manifest: List[Dict[str, Any]],
    final_action: str = "done",
) -> Dict[str, Any]:
    """
    Grade a list of agent review comments against the bug manifest.

    Parameters
    ----------
    comments      : list of dicts with keys: line_number, issue_category, severity, comment
    bug_manifest  : list of bug dicts from tasks.py
    final_action  : 'done', 'request_changes', or 'approve'

    Returns
    -------
    dict with keys:
        score           float  final normalized score (0.0–1.0)
        bugs_found      int
        bugs_missed     int
        false_positives int
        coverage        float  bugs_found / total_bugs
        precision       float  bugs_found / total_comments (if any)
        breakdown       list   per-bug detail
        feedback        str    human-readable summary
    """
    total_bugs = len(bug_manifest)
    if total_bugs == 0:
        return {"score": 1.0, "feedback": "No bugs to find — perfect!", "bugs_found": 0,
                "bugs_missed": 0, "false_positives": 0, "coverage": 1.0, "precision": 1.0,
                "breakdown": []}

    # Track which bugs have been found (to avoid double-counting)
    found_bug_ids = set()
    matched_comment_indices = set()
    raw_score = 0.0
    breakdown = []

    # For each planted bug, find the best matching comment
    for bug in bug_manifest:
        best_match_idx = None
        best_match_score = 0.0

        for idx, comment in enumerate(comments):
            if idx in matched_comment_indices:
                continue
            line = comment.get("line_number")
            if line is None:
                continue
            if not _line_matches(line, bug):
                continue

            # This comment targets the right area — score it
            match_score = 0.30   # base: found the right line area
            if comment.get("issue_category") == bug["category"]:
                match_score += CATEGORY_SCORES.get(bug["category"], 0.05)
            if comment.get("severity") == bug["severity"]:
                match_score += SEVERITY_SCORES.get(bug["severity"], 0.05)

            if match_score > best_match_score:
                best_match_score = match_score
                best_match_idx = idx

        if best_match_idx is not None:
            found_bug_ids.add(bug["bug_id"])
            matched_comment_indices.add(best_match_idx)
            raw_score += best_match_score
            breakdown.append({
                "bug_id": bug["bug_id"],
                "found": True,
                "points_awarded": round(best_match_score, 3),
                "category_correct": comments[best_match_idx].get("issue_category") == bug["category"],
                "severity_correct": comments[best_match_idx].get("severity") == bug["severity"],
            })
        else:
            breakdown.append({
                "bug_id": bug["bug_id"],
                "found": False,
                "points_awarded": 0.0,
                "category_correct": False,
                "severity_correct": False,
            })

    # False positives: comments that didn't match any bug
    false_positive_count = len(comments) - len(matched_comment_indices)
    fp_penalty = false_positive_count * 0.15
    raw_score -= fp_penalty

    # Max possible raw score
    max_possible = total_bugs * 0.50   # 0.30 base + 0.10 category + 0.10 severity per bug

    # Completion bonus
    all_found = len(found_bug_ids) == total_bugs
    if all_found:
        raw_score += 0.20 * max_possible   # 20% bonus on top

    # Approve-with-bugs penalty
    critical_bugs_missed = any(
        b["severity"] == "critical" and b["bug_id"] not in found_bug_ids
        for b in bug_manifest
    )
    if final_action == "approve" and critical_bugs_missed:
        raw_score -= 0.50 * max_possible

    # Normalize to (0.0, 1.0) - strictly between 0 and 1
    denominator = max_possible * 1.20   # max_possible + completion bonus ceiling
    normalized = raw_score / denominator
    # Clamp to (EPSILON, 1.0-EPSILON) to ensure strictly between 0 and 1
    score = max(MIN_SCORE, min(MAX_SCORE, normalized))

    bugs_found = len(found_bug_ids)
    bugs_missed = total_bugs - bugs_found
    coverage = bugs_found / total_bugs
    precision = bugs_found / len(comments) if comments else 0.0

    # Build human-readable feedback
    lines = []
    if bugs_found == total_bugs:
        lines.append("🎉 All bugs found!")
    else:
        lines.append(f"Found {bugs_found}/{total_bugs} bugs.")
    if false_positive_count:
        lines.append(f"⚠️  {false_positive_count} false positive(s) — penalty applied.")
    if final_action == "approve" and critical_bugs_missed:
        lines.append("🚨 Approved PR with critical bugs still present — heavy penalty applied.")
    lines.append(f"Score: {score:.3f}")

    return {
        "score": round(score, 4),
        "bugs_found": bugs_found,
        "bugs_missed": bugs_missed,
        "false_positives": false_positive_count,
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "breakdown": breakdown,
        "feedback": " | ".join(lines),
    }


def partial_grade(
    comments: List[Dict[str, Any]],
    bug_manifest: List[Dict[str, Any]],
) -> float:
    """
    Quick partial score during the episode (no final action bonuses/penalties).
    Used to populate ReviewObservation.partial_score.
    """
    result = grade(comments, bug_manifest, final_action="done")
    return result["score"]