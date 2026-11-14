#!/usr/bin/env python3
"""Claude Code PreToolUse guard: branch-naming.md, decided before the push.

check-branch-name.py decides the rule; CI runs it on a pull request, which is
after the name is already on the remote and the only fix is to close the pull
request and open another. This guard runs the same judgement at the one moment
the name is still free to change: when an agent is about to run `git push`.

It reads the hook payload Claude Code writes to stdin, finds every `git push`
in the Bash command, works out which branch name each one would create on the
remote, and hands that name to check-branch-name.py's own `judge()` and
`outside()`. The conditions are stated once, in that script, and nowhere here.

Which name a push creates:

    git push origin HEAD:feat/113-x   the destination of the refspec
    git push origin some-branch       that branch
    git push / git push -u origin     the branch the working copy is on

A push that creates no branch — `--delete`, `--tags` alone, a refspec under
refs/tags/ — has nothing for the rule to decide and passes.

Exit 0 lets the command run. Exit 2 refuses it, and Claude Code hands stderr
back to the agent as the reason, which is what makes the refusal actionable:
the message says which name failed, which condition, and the shape expected.

Standard library only. The command is split with shlex, which is not a shell:
a push assembled at runtime (`eval`, a variable holding "push") is not seen.
That is the gap a pre-push git hook or a forge ruleset closes, and
rules/branch-naming.md says so.

Usage (wired by hooks/hooks.json; by hand for a test):
    echo '{"tool_name":"Bash","tool_input":{"command":"git push"}}' \
        | python3 contributing/hooks/guard-push.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check-branch-name.py"

# Shell operators that end one command and start the next. shlex keeps them as
# their own tokens when punctuation_chars is on.
SEPARATORS = frozenset({"&&", "||", ";", "|", "&", "(", ")"})

# A redirection and its target (`2>&1`, `> out.txt`, `<in`). Dropped before the
# line is split, so a redirected push is not read as carrying a refspec.
REDIRECTION = re.compile(r"\d*[<>]{1,2}(?:&\d+|\s*[^\s;&|()]+)")

# git's global options that take a value as the next word. Anything else that
# starts with "-" before the subcommand is a flag with no value.
GIT_VALUED = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})

# push options that take a value as the next word.
PUSH_VALUED = frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"})

# push options under which no branch is created, so the rule has nothing to decide.
NO_BRANCH = frozenset({"-d", "--delete", "--tags", "--prune"})


def load_checker():
    """check-branch-name.py as a module; its file name is not importable as is."""
    spec = importlib.util.spec_from_file_location("check_branch_name", CHECKER)
    module = importlib.util.module_from_spec(spec)
    # A dataclass looks its module up in sys.modules while it is being built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def commands(line: str) -> list[list[str]]:
    """The simple commands in a shell line, each as its list of words."""
    line = REDIRECTION.sub(" ", line)
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    found: list[list[str]] = [[]]
    for token in lexer:
        if token in SEPARATORS:
            found.append([])
            continue
        found[-1].append(token)
    return [words for words in found if words]


def split_git(words: list[str]) -> tuple[str | None, list[str]] | None:
    """(the -C directory, the words after `push`) when the command is a git push."""
    if not words or Path(words[0]).name != "git":
        return None
    directory, index = None, 1
    while index < len(words) and words[index].startswith("-"):
        if words[index] == "-C" and index + 1 < len(words):
            directory = words[index + 1]
        index += 2 if words[index] in GIT_VALUED else 1
    if index < len(words) and words[index] == "push":
        return directory, words[index + 1 :]
    return None


def positionals(arguments: list[str]) -> tuple[list[str], bool]:
    """The push's non-option words, and whether an option means no branch is made."""
    found, no_branch, index = [], False, 0
    while index < len(arguments):
        word = arguments[index]
        no_branch = no_branch or word in NO_BRANCH
        if word in PUSH_VALUED:
            index += 2
            continue
        if not word.startswith("-"):
            found.append(word)
        index += 1
    return found, no_branch


def destination(refspec: str) -> str | None:
    """The branch a refspec writes to on the remote, or None for a tag or HEAD."""
    target = refspec.lstrip("+").split(":")[-1]
    if not target or target.startswith("refs/tags/"):
        return None
    return re.sub(r"^refs/heads/", "", target)


def current_branch(directory: str | None) -> str:
    """The branch the working copy is on, read where the push would run.

    symbolic-ref rather than rev-parse: it answers on a branch with no commits
    yet, and fails on a detached checkout, which is then read as HEAD.
    """
    where = ["-C", directory] if directory else []
    result = subprocess.run(
        ["git", *where, "symbolic-ref", "--quiet", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "HEAD"


def pushed_names(words: list[str]) -> list[str]:
    """Every branch name this one command would create on the remote."""
    parsed = split_git(words)
    if parsed is None:
        return []
    directory, arguments = parsed
    found, no_branch = positionals(arguments)
    if no_branch:
        return []
    refspecs = found[1:]
    if not refspecs:
        return [current_branch(directory)]
    return [name for name in map(destination, refspecs) if name]


def refusals(command: str, checker) -> list[str]:
    """One message per failing name, across every push in the command."""
    try:
        simple = [words for line in command.splitlines() for words in commands(line)]
    except ValueError:
        return []
    messages = []
    for words in simple:
        for name in pushed_names(words):
            if checker.outside(name) or name == "HEAD":
                continue
            messages.extend(str(finding) for finding in checker.judge(name))
    return messages


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    messages = refusals(command, load_checker())
    if not messages:
        return 0
    print("\n".join(messages), file=sys.stderr)
    print(
        "Rename the branch before the first push (git branch -m <type>/<issue>-<slug>); "
        "a name that reaches the remote can only be fixed by closing its pull request.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
