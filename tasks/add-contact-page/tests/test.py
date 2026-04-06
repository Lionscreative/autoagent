"""Score: was the contact page added? Check preview + files."""
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
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
pages_ok = preview.get("pages_ok", {})

check(preview.get("homepage_ok"), 1.0, "Homepage still works")

contact_in_preview = pages_ok.get("/contact", False)
contact_in_files = any("contact/page" in f for f in file_list)
check(contact_in_preview or contact_in_files, 2.0, "Contact page exists (preview or file)")

check("form" in code or "input" in code or "kleapform" in code, 0.5, "Has form elements")
check("acme" in code or "contact" in code, 0.5, "Has contact/company info")
check(eval_data.get("tool_calls", 99) <= 30, 0.5, "Efficient")
check(len(file_list) >= 1, 0.5, "Files created")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
