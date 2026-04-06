"""Score glassmorphism weather dashboard — blur, transparency, and glass effects."""
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

def penalize(cond, pts, desc):
    global score
    if cond: score = max(0, score - pts); details.append(f"PENALTY (-{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (1 pt)
check(preview.get("homepage_ok"), 1.0, "Homepage loads")

# 2. BLUR / GLASSMORPHISM (2.5 pts)
blur_patterns = ["backdrop-blur", "backdrop-filter", "blur(", "blur-sm", "blur-md", "blur-lg", "blur-xl", "blur-2xl", "blur-3xl"]
blur_count = sum(1 for p in blur_patterns if p in content)
check(blur_count >= 1, 1.0, f"Blur effects present ({blur_count} matches)")
check(blur_count >= 3, 1.0, f"Multiple blur effects ({blur_count} matches)")

# Semi-transparent backgrounds
transparency_patterns = ["/10", "/20", "/30", "/40", "/50", "rgba(", "bg-white/", "bg-black/",
                          "bg-slate-", "bg-blue-", "bg-purple-"]
# More specific: bg-X/opacity
opacity_bg = re.findall(r'bg-\w+/\d+', content)
check(len(opacity_bg) >= 1, 0.5, f"Semi-transparent backgrounds ({len(opacity_bg)} found)")

# 3. GRADIENT BACKGROUND (1.5 pts)
gradient_patterns = ["bg-gradient-to-", "from-", "via-", "linear-gradient", "radial-gradient"]
gradient_count = sum(1 for p in gradient_patterns if p in content)
check(gradient_count >= 1, 0.5, f"Gradient background ({gradient_count} matches)")
check(gradient_count >= 3, 1.0, f"Rich gradient usage ({gradient_count} matches)")

# 4. GLASS CARD STYLING (1.5 pts)
# Semi-transparent borders
glass_border = any(x in content for x in ["border-white/", "border-slate-", "border-gray-", "border-opacity"])
check(glass_border or len(opacity_bg) >= 2, 0.5, "Glass-style borders or multiple transparent bgs")
check(any(x in content for x in ["rounded-xl", "rounded-2xl", "rounded-3xl"]), 0.5, "Large rounded corners (glass card)")
check(any(x in content for x in ["shadow-lg", "shadow-xl", "shadow-2xl"]) or "box-shadow" in content, 0.5, "Shadow on glass cards")

# 5. WEATHER CONTENT (2 pts)
weather_terms = sum(1 for w in ["temperature", "temp", "forecast", "humidity", "wind",
                                 "weather", "rain", "sun", "cloud", "celsius", "fahrenheit",
                                 "°", "mph", "km/h", "pressure", "uv"] if w in content)
check(weather_terms >= 2, 0.5, f"Weather terminology ({weather_terms} terms)")
check(weather_terms >= 5, 0.5, f"Rich weather content ({weather_terms} terms)")

# 5-day forecast
day_patterns = sum(1 for d in ["monday", "tuesday", "wednesday", "thursday", "friday",
                                "saturday", "sunday", "mon", "tue", "wed", "thu", "fri",
                                "sat", "sun", "day 1", "day 2", "day 3", "day 4", "day 5",
                                "today", "tomorrow"] if d in content)
check(day_patterns >= 3, 0.5, f"Multi-day forecast ({day_patterns} day references)")
check("grid" in content or "flex" in content, 0.5, "Layout structure for dashboard")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

# PENALTIES
penalize(blur_count == 0, 2.0, "No blur effects at all — glassmorphism core requirement")
penalize(len(opacity_bg) == 0 and "rgba(" not in content, 1.0, "No transparency — not glassmorphism")
penalize(weather_terms == 0, 1.0, "No weather content at all")

final = round(min(score, max_score) / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
