"""Score: was the contact page added? Check preview."""
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
pages_ok = preview.get("pages_ok", {})

check(preview.get("homepage_ok"), 1.5, "Homepage still works")
check(pages_ok.get("/contact", False), 2.0, "Contact page loads in preview")

# Check contact page has form elements in HTML (if we can get it)
html = preview.get("homepage_html", "").lower()
check("contact" in html or pages_ok.get("/contact", False), 0.5, "Contact link visible or page exists")
check(len(eval_data.get("files", [])) >= 1, 0.5, "Files were created/modified")
check(eval_data.get("tool_calls", 99) <= 30, 0.5, "Efficient (<30 tool calls)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
