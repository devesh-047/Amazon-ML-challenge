#!/bin/sh
# verify-setup.sh — validate this agent-team template and probe the installed
# Claude Code for the native features the workflow relies on.
#
# Portability: POSIX sh. Runs on Linux, macOS, WSL and Git Bash.
# On native Windows PowerShell, run it inside Git Bash or WSL.
#
# Usage:  sh scripts/verify-setup.sh          (from the template/repo root)
# Exit:   0 = all structural checks passed, 1 = at least one failed.

# Note: no 'set -e'; we want every check to run and report.

PASS=0
FAIL=0
WARN=0

ok()   { printf '  [PASS] %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  [WARN] %s\n' "$1"; WARN=$((WARN+1)); }
head_() { printf '\n== %s ==\n' "$1"; }

# Resolve the template root as the parent of this script's directory.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT" || { echo "cannot cd to $ROOT"; exit 1; }

printf 'Validating agent-team template at: %s\n' "$ROOT"

AGENTS="researcher planner coder tester reviewer ml-reviewer documentation integrator"
COMMANDS="workflow ml-audit integrate experiment-log"
READONLY_AGENTS="reviewer ml-reviewer"

# Print the YAML frontmatter block of a file.
# Exits non-zero if the file does not open with a '---' delimiter.
frontmatter() {
  awk '
    NR==1 { if ($0 != "---") exit 1; next }
    /^---[[:space:]]*$/ { exit 0 }
    { print }
  ' "$1"
}

# ---------------------------------------------------------------------------
head_ "1. Required files exist"
# ---------------------------------------------------------------------------
for f in CLAUDE.md README.md .gitignore .claude/skills/workflow/SKILL.md; do
  if [ -f "$f" ]; then ok "$f"; else bad "missing: $f"; fi
done
for a in $AGENTS; do
  if [ -f ".claude/agents/$a.md" ]; then ok ".claude/agents/$a.md"
  else bad "missing agent: .claude/agents/$a.md"; fi
done
for c in $COMMANDS; do
  if [ -f ".claude/commands/$c.md" ]; then ok ".claude/commands/$c.md"
  else bad "missing command: .claude/commands/$c.md"; fi
done

# Flag stray agent files not in the expected set (typos, leftovers).
for f in .claude/agents/*.md; do
  [ -f "$f" ] || continue
  base=$(basename "$f" .md)
  case " $AGENTS " in
    *" $base "*) ;;
    *) warn "unexpected agent file: $f" ;;
  esac
done

# ---------------------------------------------------------------------------
head_ "2. YAML frontmatter is well formed"
# ---------------------------------------------------------------------------
for f in .claude/agents/*.md .claude/commands/*.md .claude/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  if ! fm=$(frontmatter "$f"); then
    bad "$f: does not start with a '---' frontmatter delimiter"
    continue
  fi
  # A closing delimiter must exist somewhere after line 1.
  if [ "$(tail -n +2 "$f" | grep -c '^---[[:space:]]*$')" -lt 1 ]; then
    bad "$f: frontmatter is not closed by '---'"
    continue
  fi
  if [ -z "$fm" ]; then
    bad "$f: frontmatter block is empty"
    continue
  fi
  # Every non-continuation line must look like 'key: value'.
  malformed=$(printf '%s\n' "$fm" \
    | grep -v '^[[:space:]]*$' \
    | grep -v '^[[:space:]]' \
    | grep -v '^[A-Za-z_][A-Za-z0-9_-]*:' \
    | head -n 1)
  if [ -n "$malformed" ]; then
    bad "$f: malformed frontmatter line: $malformed"
  else
    ok "$f: frontmatter parses"
  fi
done

# ---------------------------------------------------------------------------
head_ "3. Agents declare name, description and tools"
# ---------------------------------------------------------------------------
for a in $AGENTS; do
  f=".claude/agents/$a.md"
  [ -f "$f" ] || continue
  fm=$(frontmatter "$f") || continue
  miss=""
  printf '%s\n' "$fm" | grep -q '^name:'        || miss="$miss name"
  printf '%s\n' "$fm" | grep -q '^description:' || miss="$miss description"
  printf '%s\n' "$fm" | grep -q '^tools:'       || miss="$miss tools"
  if [ -n "$miss" ]; then
    bad "$a: missing frontmatter key(s):$miss"
  else
    # name must equal the filename, or Claude Code will not resolve it
    declared=$(printf '%s\n' "$fm" | sed -n 's/^name:[[:space:]]*//p' | tr -d '"'"'" | tr -d '\r')
    if [ "$declared" = "$a" ]; then
      ok "$a: name/description/tools present, name matches filename"
    else
      bad "$a: frontmatter name '$declared' does not match filename '$a'"
    fi
  fi
  # A role heading gives the agent an explicit identity in its body.
  if grep -q '^# ' "$f"; then :; else warn "$a: no '# ' role heading in body"; fi
done

# ---------------------------------------------------------------------------
head_ "4. Commands declare a description"
# ---------------------------------------------------------------------------
for c in $COMMANDS; do
  f=".claude/commands/$c.md"
  [ -f "$f" ] || continue
  fm=$(frontmatter "$f") || continue
  if printf '%s\n' "$fm" | grep -q '^description:'; then
    ok "$c: description present"
  else
    bad "$c: missing 'description:' in frontmatter"
  fi
done

# ---------------------------------------------------------------------------
head_ "5. Skill declares name and description"
# ---------------------------------------------------------------------------
for f in .claude/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  fm=$(frontmatter "$f") || continue
  n=0
  printf '%s\n' "$fm" | grep -q '^name:'        && n=$((n+1))
  printf '%s\n' "$fm" | grep -q '^description:' && n=$((n+1))
  if [ "$n" -eq 2 ]; then ok "$f: name + description present"
  else bad "$f: needs both 'name:' and 'description:'"; fi
done

# ---------------------------------------------------------------------------
head_ "6. Review agents are structurally read-only"
# ---------------------------------------------------------------------------
for a in $READONLY_AGENTS; do
  f=".claude/agents/$a.md"
  [ -f "$f" ] || continue
  tools=$(frontmatter "$f" | sed -n 's/^tools:[[:space:]]*//p')
  if printf '%s' "$tools" | grep -Eq '(^|[^A-Za-z])(Write|Edit|MultiEdit|NotebookEdit)([^A-Za-z]|$)'; then
    bad "$a: has a write tool in 'tools' but must be read-only -> $tools"
  else
    ok "$a: read-only (tools: $tools)"
  fi
done

# ---------------------------------------------------------------------------
head_ "7. No hardcoded model names (OmniRouter safety)"
# ---------------------------------------------------------------------------
hits=""
for f in .claude/agents/*.md .claude/commands/*.md .claude/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  if frontmatter "$f" | grep -q '^model:'; then hits="$hits $f"; fi
done
if [ -n "$hits" ]; then
  bad "'model:' key found in frontmatter of:$hits (pins a model; remove for routed backends)"
else
  ok "no 'model:' key in any agent, command or skill frontmatter"
fi

if grep -rniE 'claude-(3|4|opus|sonnet|haiku)[a-z0-9.-]*' .claude CLAUDE.md >/dev/null 2>&1; then
  warn "a literal Anthropic model identifier appears in the config; confirm it is only prose"
else
  ok "no literal Anthropic model identifiers in config"
fi

# ---------------------------------------------------------------------------
head_ "8. No secrets committed"
# ---------------------------------------------------------------------------
# Patterns: Anthropic-style keys, AWS access key ids, generic assigned secrets.
secret_hits=$(grep -rnIE \
  -e 'sk-[A-Za-z0-9_-]{20,}' \
  -e '(AKIA|ASIA)[0-9A-Z]{16}' \
  -e '(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9/+_-]{16,}' \
  .claude CLAUDE.md README.md 2>/dev/null | head -n 5)
if [ -n "$secret_hits" ]; then
  bad "possible secret material found:"
  printf '%s\n' "$secret_hits" | sed 's/^/         /'
else
  ok "no key/token/password literals found"
fi

if [ -f .gitignore ]; then
  n=0
  grep -q '^\.env$' .gitignore && n=$((n+1))
  grep -q '^\*\.pem$' .gitignore && n=$((n+1))
  if [ "$n" -eq 2 ]; then ok ".gitignore excludes .env and *.pem"
  else bad ".gitignore should exclude both '.env' and '*.pem'"; fi
fi

# ---------------------------------------------------------------------------
head_ "9. Cross-references point at files that exist"
# ---------------------------------------------------------------------------
refs=$(grep -rhoE '(\.claude|scripts)/[A-Za-z0-9_./-]*' CLAUDE.md README.md 2>/dev/null \
       | sed 's/[.,)`]*$//' | sort -u)
missing=""
for r in $refs; do
  case "$r" in
    */) [ -d "${r%/}" ] || missing="$missing $r" ;;
    *)  [ -e "$r" ] || [ -d "$r" ] || missing="$missing $r" ;;
  esac
done
if [ -n "$missing" ]; then
  bad "CLAUDE.md/README.md reference non-existent paths:$missing"
else
  ok "all .claude/ and scripts/ references resolve ($(printf '%s\n' "$refs" | grep -c .) checked)"
fi

# ---------------------------------------------------------------------------
head_ "10. Loop-termination and git-safety rules are present"
# ---------------------------------------------------------------------------
SKILL=".claude/skills/workflow/SKILL.md"
if [ -f "$SKILL" ]; then
  grep -qi '3 rework cycles\|maximum 3 rework' "$SKILL" \
    && ok "rework cycle limit stated in the skill" \
    || bad "no explicit rework cycle limit in $SKILL"
  grep -qi 'escalat' "$SKILL" \
    && ok "human escalation rules present" \
    || bad "no escalation rules in $SKILL"
fi
for f in CLAUDE.md "$SKILL" .claude/agents/integrator.md; do
  [ -f "$f" ] || continue
  grep -qi 'push' "$f" \
    && ok "$f: git push restriction mentioned" \
    || bad "$f: no git push restriction found"
done
grep -qi '3 rework cycles\|maximum.*3.*rework' CLAUDE.md \
  && ok "CLAUDE.md states the same 3-cycle limit" \
  || warn "CLAUDE.md does not restate the rework limit"

# ---------------------------------------------------------------------------
head_ "11. Portability of the template itself"
# ---------------------------------------------------------------------------
if grep -rn '/home/\|/Users/\|C:\\\\' .claude CLAUDE.md >/dev/null 2>&1; then
  bad "an absolute machine-specific path appears in the config"
else
  ok "no absolute machine-specific paths in .claude/ or CLAUDE.md"
fi
if [ -f .claude/settings.json ] || [ -d .claude/hooks ]; then
  warn "settings.json or hooks/ present — these are machine-specific; confirm before sharing"
else
  ok "no settings.json and no hooks shipped (nothing to clash with a teammate's setup)"
fi

# ---------------------------------------------------------------------------
head_ "12. Installed Claude Code capability probe"
# ---------------------------------------------------------------------------
if command -v claude >/dev/null 2>&1; then
  ver=$(claude --version 2>/dev/null | head -n 1)
  printf '  claude found: %s\n' "${ver:-version unknown}"
  helptext=$(claude --help 2>/dev/null)
  for feat in agents skills commands teams mcp; do
    if printf '%s' "$helptext" | grep -qi -- "$feat"; then
      printf '  [DETECTED]  mentions "%s" in --help\n' "$feat"
    else
      printf '  [absent]    no mention of "%s" in --help\n' "$feat"
    fi
  done
  cat <<'EOF'

  --help does not list interactive slash commands, so also check inside a
  session. Start `claude` in this directory and run:

      /agents      -> should list the 8 project agents
      /help        -> look for team-related commands
      /workflow    -> should be offered as a project command

  If your version exposes native Agent Teams, the 8 agents above are its
  members and nothing needs changing. If it does not, the same pipeline runs
  through sequential subagent delegation with no gate lost.
EOF
else
  warn "claude not found on PATH — capability probe skipped"
  cat <<'EOF'
        Run this script again on the machine that has Claude Code installed.
        Structural checks above are still valid; only feature detection was
        skipped. Nothing in this template depends on unverified syntax.
EOF
fi

# ---------------------------------------------------------------------------
printf '\n== Summary ==\n'
printf '  passed: %s   failed: %s   warnings: %s\n' "$PASS" "$FAIL" "$WARN"
if [ "$FAIL" -eq 0 ]; then
  printf '  RESULT: PASS — template is structurally valid and ready to copy.\n'
  exit 0
else
  printf '  RESULT: FAIL — fix the items above before sharing this template.\n'
  exit 1
fi
