"""Score SaaS dashboard — preview + file content."""
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
check(preview.get("homepage_ok"), 2.0, "Homepage loads")

# 2. BRAND NAME (1 pt)
check("taskflow" in content or "task flow" in content, 1.0, "Brand name TaskFlow visible")

# 3. SIDEBAR NAVIGATION (2 pts)
check("sidebar" in code or "aside" in code or "side-nav" in code or "sidenav" in code, 1.0, "Sidebar component in code")
nav_items = sum(1 for w in ["dashboard", "projects", "team", "settings"] if w in content)
check(nav_items >= 3, 1.0, f"Sidebar nav items ({nav_items}/4)")

# 4. KANBAN BOARD (3 pts)
kanban_columns = sum(1 for w in ["to do", "todo", "to-do"] if w in content)
kanban_columns += sum(1 for w in ["in progress", "in-progress"] if w in content)
kanban_columns += sum(1 for w in ["done", "completed", "complete"] if w in content)
check(kanban_columns >= 3, 1.5, f"Kanban columns present ({kanban_columns}/3)")
# Check for sample tasks/cards
check("task" in content or "card" in content or "item" in content, 0.75, "Sample tasks/cards present")
# Check for grid/flex layout for columns
check("grid" in code or "flex" in code or "columns" in code, 0.75, "Column layout (grid/flex)")

# 5. DESIGN QUALITY (1 pt)
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive breakpoints")
check(len(file_list) >= 3, 0.5, f"Created {len(file_list)} files")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
