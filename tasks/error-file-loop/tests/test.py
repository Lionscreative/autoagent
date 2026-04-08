"""Score error-file-loop — reproduces 'stuck_pattern:file_loop' error pattern."""
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
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code
trajectory = json.dumps(eval_data.get("trajectory", [])).lower()
finish = str(eval_data.get("finish_reason", "")).lower() + " " + str(eval_data.get("abort_reason", "")).lower()

# 1. Preview loads (2pt)
check(preview.get("homepage_ok"), 2.0, "Preview homepage loads")

# 2. No stream abort with 'file_loop' (2pt)
check("file_loop" not in finish and "file_loop" not in trajectory, 2.0, "No file_loop abort")

# 3. All 4 components exist (2pt)
comps = sum(1 for c in ["hero", "menu", "about", "contact"] if c in content)
check(comps >= 4, 2.0, f"All 4 components present ({comps}/4)")

# 4. Subtitle added to hero (1pt)
check("subtitle" in code or content.count("bella italia") >= 1, 1.0, "Hero has subtitle")

# 5. 2+ dishes in menu content (1pt)
dishes = sum(1 for d in ["pasta", "pizza", "risotto", "lasagna", "tiramisu", "gnocchi", "carbonara", "bruschetta", "ravioli"] if d in content)
check(dishes >= 2, 1.0, f"Menu has dishes ({dishes})")

# 6. Efficient (<60 tool calls) (1pt)
check(eval_data.get("tool_calls", 99) <= 60, 1.0, "Efficient (<60 tool calls)")

# 7. Brand 'Bella Italia' visible (1pt)
check("bella italia" in content, 1.0, "'Bella Italia' brand visible")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
