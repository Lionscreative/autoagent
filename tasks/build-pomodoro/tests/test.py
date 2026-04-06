"""Score Pomodoro timer — preview + file content."""
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
check(preview.get("homepage_length", 0) > 300 or len(code) > 800, 0.5, "Has content")

# 2. TIMER DISPLAY (2 pts)
check(":" in content and ("25" in content or "00" in content), 1.0, "Timer display (MM:SS format)")
check("text-" in code and any(s in code for s in ["text-4xl", "text-5xl", "text-6xl", "text-7xl", "text-8xl", "text-9xl"]), 1.0, "Large timer text")

# 3. CONTROLS (2.5 pts)
check("start" in content or "démarrer" in content or "lancer" in content, 0.75, "Start button")
check("pause" in content, 0.75, "Pause button")
check("reset" in content or "réinitialiser" in content, 0.75, "Reset button")
check("onclick" in code, 0.25, "Buttons are interactive")

# 4. POMODORO LOGIC (2 pts)
check("25" in code and ("1500" in code or "25 * 60" in code or "25*60" in code or "1500000" in code), 0.75, "25-minute work duration in code")
check("5" in code and ("300" in code or "5 * 60" in code or "5*60" in code), 0.75, "5-minute break duration in code")
check("session" in content or "compteur" in content or "completed" in content or "terminé" in content or "cycle" in content, 0.5, "Session counter")

# 5. FRENCH UI & DESIGN (1.5 pts)
french_words = ["travail", "pause", "session", "minuteur", "pomodoro", "démarrer", "réinitialiser", "terminé", "complété"]
french_found = sum(1 for w in french_words if w in content)
check(french_found >= 2 or "pomodoro" in content, 0.5, f"French UI content ({french_found} French words)")
check("usestate" in code and "useeffect" in code, 0.5, "Uses useState + useEffect for timer")
check("setinterval" in code or "settimeout" in code, 0.5, "Timer mechanism (setInterval/setTimeout)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
