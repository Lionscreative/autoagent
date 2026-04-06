"""Score quiz app — preview + file content."""
import os, json, re

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

# 2. QUIZ QUESTIONS (2.5 pts)
capital_words = ["capital", "tokyo", "paris", "london", "berlin", "madrid", "rome", "beijing", "ottawa", "canberra",
                 "washington", "brasilia", "cairo", "delhi", "moscow", "seoul", "bangkok", "lisbon", "vienna", "warsaw"]
capitals_found = sum(1 for w in capital_words if w in content)
check(capitals_found >= 3, 1.0, f"Has capital city content ({capitals_found} matches)")
# Count question-like patterns (arrays of objects with question/options)
check("question" in code and "option" in code or "answer" in code, 1.0, "Has question/answer data structure")
# Check for 10 questions
ten_q = len(re.findall(r'question|"q"', code)) >= 8  # at least 8 question references
check(ten_q or "10" in content, 0.5, "Has ~10 questions")

# 3. MULTIPLE CHOICE (2 pts)
check("option" in content or "choice" in content or "button" in content, 1.0, "Has answer options/buttons")
check("onclick" in code or "onchange" in code, 1.0, "Options are clickable")

# 4. SCORE & RESULTS (2 pts)
check("score" in content or "result" in content or "correct" in content, 1.0, "Shows score/results")
check("play again" in content or "restart" in content or "retry" in content or "reset" in content, 1.0, "Play Again button")

# 5. INTERACTIVITY & QUALITY (1.5 pts)
check("usestate" in code or "setstate" in code, 0.75, "Uses React state")
check(len(file_list) >= 3, 0.25, f"Created {len(file_list)} files")
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive design")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
