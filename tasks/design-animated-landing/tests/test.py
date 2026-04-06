"""Score animated landing page — animation and design quality."""
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

# 2. ANIMATION CLASSES (2.5 pts)
css_anim_patterns = ["animate-", "transition-", "duration-", "@keyframes", "animation:"]
css_anim_count = sum(1 for p in css_anim_patterns if p in content)
check(css_anim_count >= 1, 0.5, f"CSS animation classes ({css_anim_count} types)")
check(css_anim_count >= 3, 1.0, f"Rich CSS animations ({css_anim_count} types)")

# Framer motion / JS animations
js_anim = any(x in content for x in ["framer-motion", "motion.div", "motion.section", "motion.h",
                                       "usespring", "usescroll", "intersectionobserver",
                                       "animate(", "whileinview", "initial={", "animate={"])
check(js_anim, 1.0, "JS/Framer Motion animations")

# 3. GRADIENT HERO (1.5 pts)
gradient_patterns = ["bg-gradient-to-", "from-", "via-", "linear-gradient", "radial-gradient"]
gradient_count = sum(1 for p in gradient_patterns if p in content)
check(gradient_count >= 1, 0.5, f"Gradient present ({gradient_count} matches)")
check(gradient_count >= 3, 1.0, f"Rich gradient usage ({gradient_count} matches)")

# 4. HOVER EFFECTS (1.5 pts)
hover_patterns = ["hover:scale", "hover:shadow", "hover:translate", "hover:-translate-y",
                  "hover:bg-", "hover:text-", "hover:border-", "hover:opacity",
                  "group-hover:", "hover:ring"]
hover_count = sum(1 for p in hover_patterns if p in content)
check(hover_count >= 1, 0.5, f"Hover effects ({hover_count} types)")
check(hover_count >= 3, 1.0, f"Multiple hover interactions ({hover_count} types)")

# 5. BRAND & STATS (1.5 pts)
check("neuralflow" in content or "neural flow" in content or "neural-flow" in content, 1.0, "Brand name 'NeuralFlow' present")
# Stats / counters section
stat_indicators = sum(1 for w in ["counter", "count", "stat", "%", "+", "million", "billion",
                                   "users", "clients", "projects", "1000", "500", "100k", "99"] if w in content)
check(stat_indicators >= 2, 0.5, f"Stats/numbers section ({stat_indicators} indicators)")

# 6. DESIGN QUALITY (1 pt)
check(any(x in content for x in ["rounded-xl", "rounded-2xl", "rounded-3xl"]), 0.5, "Modern rounded corners")
check(any(x in content for x in ["shadow-lg", "shadow-xl", "shadow-2xl"]), 0.5, "Shadow depth")

# 7. EFFICIENCY (1 pt — reduced since this is harder)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

# PENALTIES
no_transitions = not any(x in content for x in ["transition", "duration-", "animate-", "motion"])
penalize(no_transitions, 2.0, "No animations at all — core requirement missing")
penalize("hover:" not in content, 1.0, "No hover effects — core requirement missing")

final = round(min(score, max_score) / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
