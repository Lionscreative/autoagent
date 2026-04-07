# How to run Sophie AutoAgent

Quick reference for running the Sophie eval loop. For the full directive, see `program-sophie.md`.

## One-time setup

### 1. Install Python deps (adds `groq` for the persona judge)

```bash
cd /Users/eliott/Documents/GitHub/autoagent
uv sync
```

### 2. Verify env vars

The autoagent `.env` must have:

```bash
GROQ_API_KEY=gsk_...   # for the persona judge (added automatically from RobotSpeed .env.local)
```

The bridge script (`scripts/sophie-eval-compose.ts` in the RobotSpeed repo)
reads `.env.local` from the RobotSpeed repo automatically, so `MINIMAX_TOKEN_PLAN_KEY`
is inherited from there.

### 3. Verify the bridge works (smoke test)

```bash
cd /Users/eliott/Documents/GitHub/RobotSpeed
echo '{"email_type":"first_contact_seo_insight","language":"fr","contact_name":"Marie Dupont","contact_email":"marie@test.fr","qualification_score":50,"lead_temperature":"warm","context_summary":"Test","website_analysis":{"domain":"test.fr","hasContent":true,"estimatedPages":5,"seoOpportunities":["dental SEO"],"quickWin":"Add pricing page"}}' \
  | npx tsx scripts/sophie-eval-compose.ts
```

Expected: JSON output with `"success":true` and an email. If you see
`MINIMAX_API_KEY not set`, check that `.env.local` exists in the RobotSpeed repo
with `MINIMAX_TOKEN_PLAN_KEY` set.

## Baseline run

```bash
cd /Users/eliott/Documents/GitHub/autoagent
set -a && source .env && set +a

rm -rf jobs/sophie-baseline && mkdir -p jobs/sophie-baseline
.venv/bin/harbor run -p tasks-sophie/ -n 1 \
  --agent-import-path agent_sophie:AutoAgent \
  -o jobs \
  --job-name sophie-baseline \
  --env-file .env -y
```

**Note on `-n 1`:** start with concurrency 1 for baseline to avoid overwhelming
MiniMax (token plan may have rate limits). Once baseline works, you can bump to
`-n 3` for faster iteration.

**Duration:** ~5-10 minutes (5 tasks × 1-2 min each including MiniMax retries + 3 Groq judge calls per task).

## Check results

### Quick scan

```bash
for d in jobs/sophie-baseline/*/; do
  name=$(basename "$d")
  reward=$(cat "$d/verifier/reward.txt" 2>/dev/null || echo "?")
  echo "$name: $reward"
done
```

### Average score

```bash
python3 -c "
import os, glob
scores = []
for f in glob.glob('jobs/sophie-baseline/*/verifier/reward.txt'):
    try: scores.append(float(open(f).read().strip()))
    except: pass
print(f'Avg: {sum(scores)/len(scores):.3f} | N: {len(scores)} | Scores: {scores}')
"
```

### Detailed scoring for one task

```bash
cat jobs/sophie-baseline/french-dentist-trial/verifier/stdout.txt
```

This shows:
- The subject line and body
- Each hard rule pass/fail with reason
- Each persona judge's verdict with `deal_breaker` and `what_worked`
- Final hard/soft/total score

## Experiment loop (after baseline)

1. Read the baseline results. Identify the dominant failure pattern.
2. Make ONE targeted change in `/Users/eliott/Documents/GitHub/RobotSpeed/libs/agent-inbound/composer.ts`
3. Commit in the RobotSpeed repo: `cd /Users/eliott/Documents/GitHub/RobotSpeed && git commit -am "experiment(sophie): <change>"`
4. Run the experiment:

```bash
cd /Users/eliott/Documents/GitHub/autoagent
EXP_NAME="sophie-exp-001-shorter-prompt"
rm -rf "jobs/$EXP_NAME" && mkdir -p "jobs/$EXP_NAME"
.venv/bin/harbor run -p tasks-sophie/ -n 1 \
  --agent-import-path agent_sophie:AutoAgent \
  -o jobs \
  --job-name "$EXP_NAME" \
  --env-file .env -y
```

5. Compare scores:

```bash
echo "Baseline:" && python3 -c "
import glob; s=[float(open(f).read()) for f in glob.glob('jobs/sophie-baseline/*/verifier/reward.txt')]
print(f'  Avg {sum(s)/len(s):.3f} | {s}')
"
echo "Exp:" && python3 -c "
import glob; s=[float(open(f).read()) for f in glob.glob('jobs/$EXP_NAME/*/verifier/reward.txt')]
print(f'  Avg {sum(s)/len(s):.3f} | {s}')
"
```

6. Keep or discard:
   - **Keep:** avg improved → leave the RobotSpeed commit in place
   - **Discard:** avg regressed → `cd /Users/eliott/Documents/GitHub/RobotSpeed && git revert HEAD`

7. Log to `results.tsv`:

```bash
echo -e "$(git -C ../RobotSpeed rev-parse --short HEAD)\t<avg>\t<passed>/5\t<scores>\t<cost>\tkeep\tshorter prompt FR" >> results.tsv
```

8. Repeat.

## Current task set (5 validation tasks)

| Task | Language | Email type | Edge case |
|------|----------|------------|-----------|
| `french-dentist-trial` | fr | `nudge_complete_onboarding` | Happy path FR |
| `business-name-as-firstname` | fr | `first_contact_seo_insight` | Business name used as first name |
| `german-contact-onboarding` | de | `first_contact_seo_insight` | German language, must be 100% DE |
| `generic-email-prefix` | en | `first_contact_seo_insight` | `support@` contact, no real name |
| `ecommerce-english-first-contact` | en | `first_contact_seo_insight` | English e-commerce happy path |

## Scoring breakdown (per task, total 10 pts)

### HARD RULES (5 pts, deterministic)

| Check | Points |
|-------|--------|
| No CJK / Arabic / Cyrillic characters | 1 |
| No wrong-language word leaks | 1 |
| No em-dashes or semicolons | 1 |
| Greeting does not use business/generic word | 1 |
| Required terms present (task-specific) | 1 |

### SOFT JUDGE (5 pts, Groq Llama persona)

3 personas are asked separately, scores averaged. Each persona scores 0-5:

| Signal | Max |
|--------|-----|
| `would_reply` (binary) | 2.0 |
| `feels_personal_to_me` / 10 × 1.5 | 1.5 |
| `trust_signals` / 10 × 1.0 | 1.0 |
| `(10 - feels_like_ai) / 10` × 0.5 | 0.5 |

Personas are tuned with an **anti-sycophancy anchor**: "default to would_reply=false. Be ruthless. Most cold emails are trash."

## Troubleshooting

### "MINIMAX_API_KEY environment variable is not set"

The bridge TS script must be run from the RobotSpeed repo directory (it loads `.env.local` relative to cwd). If running manually, `cd /Users/eliott/Documents/GitHub/RobotSpeed` first.

When run via `agent_sophie.py`, the subprocess sets `cwd=ROBOTSPEED_REPO` automatically.

### "groq library not installed"

```bash
cd /Users/eliott/Documents/GitHub/autoagent
uv sync
```

### "GROQ_API_KEY not set"

Check `/Users/eliott/Documents/GitHub/autoagent/.env` has `GROQ_API_KEY=gsk_...`.
If missing, copy from the RobotSpeed repo:

```bash
grep "GROQ_API_KEY=" /Users/eliott/Documents/GitHub/RobotSpeed/.env.local >> .env
```

### A task shows reward=0.0 with "SUCCESS: false"

The bridge crashed. Check the trajectory:

```bash
cat jobs/sophie-baseline/<task-name>/trajectory.json | jq '.final_metrics.extra'
```

If "error" is set, look for the stack trace in the step message.

### Verifier says "JUDGE SKIPPED"

Either `groq` is not installed (run `uv sync`) or `GROQ_API_KEY` is not set.
In this case the soft score defaults to 2.5/5 (neutral midpoint), so hard rules dominate.

## File layout

```
autoagent/
├── agent_sophie.py                      # Harbor adapter (this repo)
├── program-sophie.md                    # Meta-agent directive
├── RUN-SOPHIE.md                        # This file
├── tasks-sophie/
│   ├── _verifier_lib.py                 # Shared verifier (hard rules + persona judge)
│   ├── french-dentist-trial/
│   │   ├── task.toml
│   │   ├── instruction.md               # JSON prospect spec
│   │   └── tests/test.py                # Task-specific verifier config
│   ├── business-name-as-firstname/
│   ├── german-contact-onboarding/
│   ├── generic-email-prefix/
│   └── ecommerce-english-first-contact/
└── jobs/sophie-baseline/                # Run output (gitignored)

RobotSpeed/
├── scripts/sophie-eval-compose.ts       # The TS bridge (called via subprocess)
└── libs/agent-inbound/
    ├── composer.ts                      # What the meta-agent edits
    └── analyzer.ts                      # First-name dictionaries
```
