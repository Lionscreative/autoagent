"""Score bento grid startup showcase — varied grid, shadows, micro-interactions."""
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

# 2. BENTO GRID with varying spans (2.5 pts)
check("grid" in content, 0.5, "Grid layout present")
grid_cols = sum(1 for c in ["grid-cols-2", "grid-cols-3", "grid-cols-4", "grid-cols-6",
                             "grid-cols-12"] if c in content)
check(grid_cols >= 1, 0.5, f"Grid columns defined ({grid_cols} variants)")

# Varying spans — the essence of bento
span_patterns = ["col-span-2", "col-span-3", "col-span-4", "row-span-2", "row-span-3",
                 "col-span-full", "md:col-span", "lg:col-span"]
span_count = sum(1 for p in span_patterns if p in content)
check(span_count >= 1, 0.5, f"Grid spans for varied sizes ({span_count} types)")
check(span_count >= 3, 1.0, f"Rich bento grid with multiple span sizes ({span_count} types)")

# 3. SHADOWS (1.5 pts)
shadow_patterns = ["shadow-sm", "shadow-md", "shadow-lg", "shadow-xl", "shadow-2xl", "box-shadow"]
shadow_count = sum(1 for p in shadow_patterns if p in content)
check(shadow_count >= 1, 0.5, f"Shadow classes ({shadow_count} types)")
check(shadow_count >= 2, 0.5, f"Multiple shadow depths ({shadow_count} types)")
check(any(x in content for x in ["shadow-lg", "shadow-xl", "shadow-2xl"]), 0.5, "Deep shadows for depth")

# 4. MICRO-INTERACTIONS (2 pts)
hover_patterns = ["hover:shadow", "hover:scale", "hover:-translate-y", "hover:translate",
                  "hover:ring", "hover:border", "group-hover:", "hover:bg-", "hover:text-"]
hover_count = sum(1 for p in hover_patterns if p in content)
check(hover_count >= 1, 0.5, f"Hover interactions ({hover_count} types)")
check(hover_count >= 3, 0.5, f"Multiple hover micro-interactions ({hover_count} types)")

transition = any(x in content for x in ["transition-all", "transition-transform", "transition-shadow",
                                          "transition-colors", "duration-200", "duration-300", "duration-500"])
check(transition, 0.5, "Smooth transitions on interactions")
check("group" in content and "group-hover" in content, 0.5, "Group hover for card sub-elements")

# 5. BRAND & CONTENT SECTIONS (1.5 pts)
check("launchpad" in content or "launch pad" in content or "launch-pad" in content, 0.5, "Brand name 'LaunchPad' present")

sections = sum(1 for w in ["feature", "stat", "testimonial", "review", "quote", "cta",
                            "call to action", "get started", "sign up", "try", "pricing"] if w in content)
check(sections >= 2, 0.5, f"Multiple content sections ({sections} types)")
check(sections >= 4, 0.5, f"Rich content variety ({sections} types)")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

# PENALTIES
penalize(span_count == 0, 2.0, "No grid spans — not a bento grid, just a uniform grid")
penalize(hover_count == 0, 1.0, "No hover effects — micro-interactions required")
penalize(shadow_count == 0, 0.5, "No shadows at all — SaaS style needs depth")

final = round(min(score, max_score) / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
