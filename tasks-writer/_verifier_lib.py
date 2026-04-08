"""
Shared verifier library for writer-eval tasks.

Reads /tmp/eval_results.json (written by agent_writer.py before the verifier
runs inside the Docker container) and computes a reward in [0, 1] from the
composite score produced by scripts/section-writer-eval.ts.

The composite is already a 0-100 multiplicative score with floor penalty
(see libs/content-system-v2/pipeline/eval/score.ts). We just divide by 100.

Failure semantics:
  - eval_results.json missing                     → reward 0
  - success=false                                 → reward 0
  - validate-prompts failed (aborted=true)        → reward 0
  - scores.composite is null/missing              → reward 0
  - scores.composite is a number                  → reward = composite / 100

Import from each task's tests/test.py:

    import sys
    sys.path.insert(0, "/tasks-writer")
    sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-writer")
    from _verifier_lib import score_writer_eval
    score_writer_eval()
"""

import json
import os

EVAL_PATH = "/tmp/eval_results.json"
REWARD_PATH = "/logs/verifier/reward.txt"


def score_writer_eval() -> None:
    """Read eval_results.json and write reward to /logs/verifier/reward.txt."""
    os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

    if not os.path.exists(EVAL_PATH):
        print(f"[verifier] No eval results at {EVAL_PATH}, scoring 0")
        _write_reward(0.0)
        return

    try:
        eval_data = json.loads(open(EVAL_PATH).read())
    except Exception as e:
        print(f"[verifier] Failed to parse eval results: {e}")
        _write_reward(0.0)
        return

    # Print a compact summary so Harbor's trajectory logs are readable
    print("=" * 70)
    print(f"FIXTURE: {eval_data.get('fixture_id', '?')}")
    print(f"SUCCESS: {eval_data.get('success', False)}")
    if eval_data.get("aborted"):
        print(f"ABORTED: {eval_data.get('error', '?')}")
    print("-" * 70)

    if not eval_data.get("success"):
        print(f"[verifier] Eval FAILED or aborted — reward 0")
        print(f"  error: {eval_data.get('error', 'unknown')}")
        _write_reward(0.0)
        return

    scores = eval_data.get("scores") or {}
    composite = scores.get("composite")

    if composite is None or not isinstance(composite, (int, float)):
        print(f"[verifier] composite is missing or non-numeric — reward 0")
        print(f"  scores: {scores}")
        _write_reward(0.0)
        return

    raw_geomean = scores.get("raw_geometric_mean", 0)
    floor_triggered = scores.get("floor_triggered", False)
    below_floor = scores.get("below_floor", [])

    print(f"composite      : {composite:.2f}/100")
    print(f"raw geomean    : {raw_geomean:.2f}/100")
    print(f"floor triggered: {floor_triggered}")
    if below_floor:
        print(f"below floor    : {', '.join(below_floor)}")
    print("-" * 70)
    print(f"  winston    : {scores.get('winston', 0):>6}")
    print(f"  factuality : {scores.get('factuality', 0):>6}")
    print(f"  originality: {scores.get('originality', 0):>6}")
    print(f"  seo        : {scores.get('seo', 0):>6}")
    print(f"  specificity: {scores.get('specificity', 0):>6}")

    costs = eval_data.get("costs") or {}
    latency = eval_data.get("latency") or {}
    print("-" * 70)
    print(f"cost writer    : ${float(costs.get('writer_usd', 0) or 0):.4f}")
    print(f"cost judges    : ${float(costs.get('judges_usd', 0) or 0):.4f}")
    print(f"cost total     : ${float(costs.get('total_usd', 0) or 0):.4f}")
    print(f"latency writer : {int(latency.get('writer_ms', 0) or 0)}ms")

    # Reward = composite / 100, clamped to [0, 1]
    reward = max(0.0, min(1.0, composite / 100.0))
    rounded = round(reward, 4)
    print("=" * 70)
    print(f"REWARD: {rounded}")
    print("=" * 70)

    _write_reward(rounded)


def _write_reward(value: float) -> None:
    with open(REWARD_PATH, "w") as f:
        f.write(str(value))
