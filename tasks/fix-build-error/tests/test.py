"""Score: did the agent fix the build error? Check preview."""
import os, json

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
score = 0.0
max_score = 5.0
details = []

def check(cond, pts, desc):
    global score
    if cond: score += pts; details.append(f"PASS ({pts}): {desc}")
    else: details.append(f"FAIL (0/{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})

# The ONLY thing that matters: does the preview work?
check(preview.get("homepage_ok"), 3.0, "Homepage loads after fix (no errors)")
check(preview.get("homepage_length", 0) > 200, 1.0, "Page has content")
check(eval_data.get("tool_calls", 99) <= 20, 0.5, "Fixed efficiently (<20 tool calls)")
check(eval_data.get("duration_ms", 999999) <= 120000, 0.5, "Fixed quickly (<2min)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
