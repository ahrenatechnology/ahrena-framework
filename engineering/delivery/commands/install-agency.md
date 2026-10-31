---
name: install-agency
description: Install the agency in this repository, or report what is missing — enable its plugins in settings.json and write the entry directive, idempotently.
type: command
clade: engineering
subclade: delivery
argument-hint: "[--check] [--platform claude|codex] [--language python|typescript|go|rust]"
references:
  - skills/installing-the-agency/SKILL.md
---

# /install-agency

Invoke `installing-the-agency` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `--check` | no | Report the directive and each plugin as enabled, missing or disabled, writing nothing. Without it, the plugins are enabled and the directive is written or refreshed |
| `--platform claude\|codex` | no | Override the auto-detected platform when the repository carries both `CLAUDE.md` and `AGENTS.md`. `codex` skips `.claude/settings.json` |
| `--language python\|typescript\|go\|rust` | no | Enable that language plugin instead of the ones detected from the repository's marker files. Repeatable, or a comma list |

Without `--check` the skill ensures the plugins and the directive are in place;
the write is idempotent, so a re-run on an already-installed repository changes
nothing. The skill runs its script from the plugin's own root:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/installing-the-agency/scripts/install.py" [arguments]
```

On Codex the script is the skill's own `scripts/install.py`.

## What runs

`skills/installing-the-agency`, from step 1.
