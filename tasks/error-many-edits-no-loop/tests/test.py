"""Score error-many-edits-no-loop — reproduces 'stuck_pattern:restart_diagnose_loop'."""
import os, json

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
score = 0.0
max_score = 10.0
details = []

def check(cond, pts, desc):
    global score
    if cond: score += pts; details.append(f"PASS ({pts}): {desc}")
    else: details.append(f"FAIL (0/{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code
trajectory = json.dumps(eval_data.get("trajectory", [])).lower()
finish = str(eval_data.get("finish_reason", "")).lower() + " " + str(eval_data.get("abort_reason", "")).lower()

# 1. Preview loads (2pt)
check(preview.get("homepage_ok"), 2.0, "Preview homepage loads")

# 2. No restart_diagnose_loop abort (3pt)
check("restart_diagnose_loop" not in finish and "restart_diagnose_loop" not in trajectory, 3.0, "No restart_diagnose_loop abort")

# 3. All 4 sections (2pt)
sections = sum(1 for w in ["stats", "activity", "chart", "quick action", "quickaction"] if w in content)
check(sections >= 4, 2.0, f"4 sections present ({sections})")

# 4. Icons used (1pt)
check("lucide" in code or "svg" in code or "icon" in code, 1.0, "Icons used")

# 5. Sidebar present (1pt)
check("sidebar" in code or "aside" in code, 1.0, "Sidebar present")

# 6. Efficient (<80 tool calls) (1pt)
check(eval_data.get("tool_calls", 99) <= 80, 1.0, "Efficient (<80 tool calls)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
