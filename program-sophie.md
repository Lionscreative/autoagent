# Sophie AutoAgent — RobotSpeed Inbound Agent Optimization

You are a meta-agent that improves **Sophie**, the RobotSpeed inbound cold email
composer. Sophie runs in production and writes personalized emails to prospects
based on their profile, language, and funnel stage.

Unlike standard AutoAgent, you are NOT modifying `agent.py`. You are modifying
the **Sophie email composer** in a separate repo, in production.

## Architecture

```
Harbor benchmark tasks (prospect specs as JSON)
  → agent_sophie.py (the harness) reads each task
    → Calls /Users/eliott/Documents/GitHub/RobotSpeed/scripts/sophie-eval-compose.ts
      → Runs composeEmail() with a mocked QualificationResult
      → Hits MiniMax M2.7 via the real production API (token plan)
      → Returns {subject, body_text, body_html}
  → Verifier (tests/test.py) scores the email:
    - HARD RULES (5 pts): regex checks for language leaks, format, greeting, required terms
    - SOFT JUDGE (5 pts): Groq Llama 3.3 70B with 3 persona judges + anti-sycophancy anchor
  → You analyze scores, find patterns in failures, edit Sophie, re-run
```

## Critical Constraint — MiniMax M2.7 stays

We are bootstrap. We have a prepaid **MiniMax token plan**. We CANNOT switch
models. Every optimization must work within MiniMax M2.7's behavior.

Known MiniMax M2.7 quirks:
- Thinking model (reasons in English via `<think>` tags, which we strip)
- Leaks English verbs into French/German output when prompt is long
- Leaks CJK characters occasionally (we think from reasoning phase)
- Responds well to explicit examples, less well to abstract instructions
- Attention decays on prompts >4000 tokens — the end of the prompt matters more

## What You Can Modify

Files in `/Users/eliott/Documents/GitHub/RobotSpeed/libs/agent-inbound/`:

- **`composer.ts`** — the main file (1806 lines). Contains:
  - `PERSONA_SYSTEM_PROMPT_FR` (line ~94) — French system prompt for MiniMax
  - `PERSONA_SYSTEM_PROMPT_EN` — English system prompt
  - `PERSONA_SYSTEM_PROMPT_DE` — German system prompt
  - `composeEmail()` — the main function (line ~846)
  - `validateEmail()` — post-generation regex validation
  - `postProcessBody()` — post-processing cleanup
  - `deriveFirstName()` — first name extraction logic
  - JSON schema descriptions for subject/body
  - Temperature, maxOutputTokens, retry logic

- **`analyzer.ts`** — contains `FRENCH_FIRST_NAMES` and `GERMAN_FIRST_NAMES` sets.
  You can add/remove names if name detection fails tasks.

**Do NOT modify:**
- Files outside `libs/agent-inbound/` in the RobotSpeed repo
- `agent_sophie.py` (the eval harness)
- `scripts/sophie-eval-compose.ts` (the bridge)
- Task files in `tasks-sophie/`
- Verifier code in `tasks-sophie/_verifier_lib.py`

## Goal

Maximize the average score across all 5 validation tasks in `tasks-sophie/`.

Baseline target: discover it on the first run. Hill-climb from there.

## How to Run Benchmarks

```bash
cd /Users/eliott/Documents/GitHub/autoagent
set -a && source .env && set +a

# Baseline run
rm -rf jobs/sophie-baseline && mkdir -p jobs/sophie-baseline
.venv/bin/harbor run -p tasks-sophie/ -n 1 \
  --agent-import-path agent_sophie:AutoAgent -o jobs \
  --job-name sophie-baseline --env-file .env -y

# Experiment run (after editing composer.ts)
rm -rf jobs/sophie-exp-001 && mkdir -p jobs/sophie-exp-001
.venv/bin/harbor run -p tasks-sophie/ -n 1 \
  --agent-import-path agent_sophie:AutoAgent -o jobs \
  --job-name sophie-exp-001 --env-file .env -y
```

Each run takes ~5-10 minutes (5 tasks × ~1-2 min each).

### Check results

```bash
# Quick scan
for d in jobs/sophie-baseline/*/; do
  name=$(basename "$d")
  reward=$(cat "$d/verifier/reward.txt" 2>/dev/null || echo "?")
  echo "$name: $reward"
done

# Average score
python3 -c "
import os, glob
scores = []
for f in glob.glob('jobs/sophie-baseline/*/verifier/reward.txt'):
    try: scores.append(float(open(f).read().strip()))
    except: pass
print(f'Avg: {sum(scores)/len(scores):.3f} | N: {len(scores)} | Scores: {scores}')
"

# Detailed stdout from a specific task
cat jobs/sophie-baseline/french-dentist-trial/verifier/stdout.txt
```

## Experiment Loop

1. **Baseline first.** Always. Never skip this.
2. Read `run.log` and per-task verifier stdout to understand the failure patterns.
3. Group failures by **root cause** (not by task). Examples of patterns:
   - "All FR tasks leak 'publish' — the language_rule isn't enough"
   - "Greeting uses business name on 2/5 tasks — deriveFirstName not strict enough"
   - "Persona judges all say 'feels generic' — prompt encourages templating"
4. Choose **ONE** minimal targeted change that addresses a pattern.
5. Make the change in `composer.ts` (or `analyzer.ts`).
6. Commit the change in the RobotSpeed repo: `git commit -m "experiment(sophie): ..."`
7. Rebuild nothing (no Docker for Sophie — the bridge runs directly on the host via `npx tsx`).
8. Rerun the benchmark with a new job name (`exp-001`, `exp-002`...).
9. Compare average score to baseline.
10. **Keep/Discard:**
    - If avg score improved → keep, commit to main
    - If avg score stayed the same AND the code is simpler → keep
    - Otherwise → `cd /Users/eliott/Documents/GitHub/RobotSpeed && git checkout libs/agent-inbound/composer.ts`
11. Record the experiment in `results.tsv` (see below).
12. Repeat.

## Logging Results

Log every experiment to `/Users/eliott/Documents/GitHub/autoagent/results.tsv`:

```
commit	avg_score	passed	task_scores	cost_usd	status	description
```

- `commit`: short git hash in the RobotSpeed repo (`git -C ../RobotSpeed rev-parse --short HEAD`)
- `avg_score`: average reward across all 5 tasks
- `passed`: how many tasks scored ≥ 0.7 (arbitrary pass threshold)
- `task_scores`: comma-separated per-task scores
- `cost_usd`: from trajectory.json final_metrics.total_cost_usd summed
- `status`: `keep` / `discard` / `crash`
- `description`: one-line summary

## Anti-Overfitting Rules

**The validation set is small (5 tasks).** You will be tempted to make task-specific
changes. Don't.

Use this test before any edit: **"If this exact prospect disappeared, would this
still be a worthwhile change?"**

If the answer is no, you're overfitting. Examples of overfitting:
- ❌ Adding "Marie Dupont" to a hardcoded prospect list
- ❌ Special-casing "Mon Chauffeur Privé" in `deriveFirstName()`
- ❌ Adding a French-only regex that only matches dentist-related keywords

Examples of good generalization:
- ✅ Improving `deriveFirstName()` to reject ALL business names starting with
  possessive articles
- ✅ Strengthening the `<language_rule>` section of the system prompt
- ✅ Lowering temperature from 0.7 to 0.3 (affects all languages)

## Failure Analysis Patterns

When a task fails, check:

1. **Bridge failure** (`eval_data.success = false`)
   → Sophie crashed. Check stderr in the trajectory. Fix the bug in composer.ts.

2. **Hard rule failure**
   → Look at which rule failed (the stdout shows `HARD FAIL (0/X): description`).
   → Common fixes:
     - Language leak → strengthen `<language_rule>`, lower temperature, add end-of-prompt reminder
     - Bad greeting → improve `deriveFirstName()` logic
     - Em-dash present → the model is ignoring the formatting rule (prompt issue)

3. **Soft judge failure** (low persona scores)
   → Read the `deal_breaker` and `what_worked` fields in the verifier stdout.
   → Common fixes:
     - "Feels generic" → the `<principles>` section needs more specificity anchoring
     - "Flattery / fake observation" → the prompt encourages observations even when
       no website data is available. Add logic to skip observations when data is thin.
     - "Pushing too hard" → the persona is rejecting the CTA intensity

## Simplicity Criterion

All else being equal, simpler wins.

Sophie's `composer.ts` is 1806 lines. Many sections are defensive bandaids from
past firefights. If you find a simpler implementation that achieves the same
score, **keep the simpler one**, even if it means deleting 50 lines of defense.

## NEVER STOP

Once the experiment loop begins, do NOT stop to ask whether to continue.
Keep iterating until the human explicitly interrupts you.

Record results, learn from discards, keep improving.
