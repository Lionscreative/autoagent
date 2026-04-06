"""Score todo app — preview + file content."""
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

# 1. PREVIEW (2 pts)
check(preview.get("homepage_ok"), 1.5, "Homepage loads")
check(preview.get("homepage_length", 0) > 500 or len(code) > 1000, 0.5, "Substantial content")

# 2. INPUT & ADD TASK (2 pts)
check("input" in content or "type=\"text\"" in content, 1.0, "Has text input for new task")
check("add" in content or "submit" in content or "create" in content, 1.0, "Has add/submit action")

# 3. CATEGORIES (2 pts)
categories_found = sum(1 for c in ["work", "personal", "shopping"] if c in content)
check(categories_found >= 2, 1.0, f"Has categories ({categories_found}/3)")
check("select" in content or "option" in content or "category" in content, 1.0, "Category selector present")

# 4. TASK ACTIONS (2 pts)
check("delete" in content or "remove" in content or "trash" in content, 1.0, "Can delete tasks")
check("done" in content or "complete" in content or "check" in content or "line-through" in content, 1.0, "Can mark as done")

# 5. INTERACTIVITY & DARK THEME (2 pts)
check("usestate" in code or "setstate" in code, 0.75, "Uses React state")
check("onchange" in code or "onclick" in code or "onsubmit" in code, 0.25, "Has event handlers")
dark_indicators = sum(1 for d in ["dark", "bg-gray-9", "bg-gray-8", "bg-slate-9", "bg-slate-8", "bg-zinc-9", "bg-zinc-8", "#1", "#0", "bg-black"] if d in code)
check(dark_indicators >= 2, 0.5, f"Dark theme classes ({dark_indicators} indicators)")
check(len(file_list) >= 3, 0.5, f"Created {len(file_list)} files")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
