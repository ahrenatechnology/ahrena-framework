---
id: backstage-language
type: rule
clade: engineering
subclade: quality
title: Backstage in English, the user's language on screen
statement: Names behind the scenes are English — code, paths, routes, keys, env vars, CLI options, tests, commits; the user's language is only in what they read.
enforcement: judgment
references:
  - docs/backstage-language.md
---

# Backstage in English, the user's language on screen

Everything a program is built from is named in English. The user's language — Portuguese, for most products built on this framework today — lives only in what a person reads: screen text, labels, messages to the user, and the conversation with them. [`docs/backstage-language.md`](../docs/backstage-language.md) carries the argument, the measurements and the cases the script cannot see.

**Behind the scenes, in English:** code and identifiers, file and directory names, API routes and parameters, URLs, CSS classes, JSON keys, tables and columns, CLI options, environment variables, test names, and commit messages.

**On screen, in the user's language:** screen text, labels, messages to the user, and the conversation.

A new name in the user's language behind the scenes is a reason to request changes in review, **even when the code around it does not follow this rule yet**. The rule binds the name a change writes, not the names it passes; renaming what already exists is separate work, owned by its own issue.

## Conditions

1. **A name a change writes in a name position carries no Portuguese diacritic and no segment on the closed Portuguese word list.** A diacritic is one of `á à â ã é ê í ó ô õ ú ü ç`. A segment is a run of the name split on camelCase, snake_case, kebab-case, dots and slashes, matched whole against the list in the hook, which holds only words that are not also English. A name position is a declaration, a key or member at the start of a line, a declaring assignment, an environment-variable member or `.env` key, a CSS selector or custom property, a `className` value, an SQL table or column definition, and a string literal whose whole shape is a key, a route, a URL path or parameter name, a CLI option or an `UPPER_SNAKE` variable name. Text inside a string literal or a comment is never a name. A line carrying an `ADR-N` pointer is exempt. Decided by [`hooks/check-backstage-language.py`](../hooks/check-backstage-language.py), over the lines `--changed` scopes it to.
2. **A path a change adds or renames into place has no segment that fails condition 1's two tests.** Decided by [`hooks/check-backstage-language.py`](../hooks/check-backstage-language.py), over the added and renamed paths `--changed` reports; a file the change only edits keeps its path unchecked.
3. **Every other name behind the scenes is English.** A Portuguese word not on the list, a function parameter, a destructured binding, an import alias, a name in a template language the hook does not lex, a test name written as a sentence, and a commit subject are each read by a reviewer against this rule. Decided by a reviewer.

## Where this stops

**The hook can only miss, never misfire on English.** Its word list excludes every word that is also English (`data`, `total`, `valor`, `tempo`, `pasta`), and it reads names only in name positions, so a pass from it is not a pass from the rule. Condition 3 is what remains, and it is the larger half.

**A name a contract fixes is not the author's to translate.** A field of an external API, a column of a database the service only reads, a key a partner sends: the line carries `ADR-N` pointing at the decision to keep it, and a recorded fixture of such an API is left out with `--exclude <glob>`. A domain term with no English equivalent — `CPF`, `CNPJ`, `Pix` — is a proper noun of the domain, kept by [`ubiquitous-language.md`](ubiquitous-language.md), not a Portuguese word to translate.

**It does not reach the screen.** Which language the user reads, how screen text is organised for translation, and whether a product ships several languages are product decisions this rule does not make.

**It does not demand a migration.** Existing Portuguese names are outside a change's scope until that change renames them. A codebase converges because each change stops adding to the debt, and the rename of what is already there is planned as its own work.
