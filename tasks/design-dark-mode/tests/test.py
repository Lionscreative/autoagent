"""Score dark mode portfolio — design pattern quality."""
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

# 2. DARK BACKGROUNDS (2.5 pts)
dark_bg_patterns = ["bg-gray-900", "bg-black", "bg-slate-900", "bg-zinc-900", "bg-neutral-900",
                     "bg-gray-950", "bg-slate-950", "bg-zinc-950", "bg-neutral-950"]
dark_bg_count = sum(1 for p in dark_bg_patterns if p in content)
check(dark_bg_count >= 1, 1.0, f"Dark background classes ({dark_bg_count} types)")
check(dark_bg_count >= 3, 1.0, f"Multiple dark background variants ({dark_bg_count} types)")
# Also check CSS custom properties or inline styles
dark_css = any(x in content for x in ["#000", "#111", "#1a1a", "#0a0a", "#121212", "rgb(0", "rgb(17", "rgb(10"])
check(dark_bg_count >= 2 or dark_css, 0.5, "Consistent dark theme throughout")

# 3. ACCENT COLORS (2 pts)
accent_patterns = ["blue-400", "blue-500", "blue-600", "cyan-400", "cyan-500",
                   "green-400", "green-500", "emerald-400", "emerald-500",
                   "violet-400", "violet-500", "purple-400", "purple-500",
                   "indigo-400", "indigo-500", "teal-400", "teal-500",
                   "#00ff", "#0ff", "#0f0", "neon", "electric"]
accent_count = sum(1 for p in accent_patterns if p in content)
check(accent_count >= 1, 1.0, f"Accent color used ({accent_count} matches)")
check(accent_count >= 3, 1.0, f"Rich accent color palette ({accent_count} matches)")

# 4. GRID LAYOUT (1.5 pts)
check("grid" in content, 0.5, "Grid layout present")
grid_cols = any(x in content for x in ["grid-cols-2", "grid-cols-3", "grid-cols-4", "gridtemplatecol"])
check(grid_cols, 0.5, "Grid columns defined")
check("gap-" in content or "gap:" in content, 0.5, "Grid gap spacing")

# 5. BRAND NAME (1 pt)
check("alex nova" in content, 1.0, "Brand name 'Alex Nova' present")

# 6. DESIGN QUALITY (1 pt)
check(any(x in content for x in ["rounded", "rounded-lg", "rounded-xl"]), 0.5, "Rounded corners")
check(any(x in content for x in ["hover:", "transition", "duration-"]), 0.5, "Interactive effects")

# 7. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

# PENALTIES — anti-patterns for dark mode
bg_white_count = content.count("bg-white")
penalize(bg_white_count >= 3, 1.5, f"Too many bg-white ({bg_white_count}x) — should be dark")
light_border_count = sum(content.count(b) for b in ["border-gray-200", "border-gray-300", "border-gray-100"])
penalize(light_border_count >= 3, 1.0, f"Light borders in dark theme ({light_border_count}x)")
penalize("text-gray-900" in content and "bg-gray-900" in content and content.count("text-gray-900") > content.count("bg-gray-900"), 0.5, "Dark text on dark bg — contrast issue")

final = round(min(score, max_score) / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
