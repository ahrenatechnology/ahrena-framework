---
id: backstage-language
type: doc
clade: engineering
subclade: quality
title: Backstage in English, the user's language on screen
summary: Why every name behind the scenes is English while the user reads their own language, how the hook decides part of that without a dictionary, and what a reviewer still owns.
references:
  - rules/backstage-language.md
  - docs/ubiquitous-language.md
---

# Backstage in English, the user's language on screen

This document is the companion of [`rules/backstage-language.md`](../rules/backstage-language.md). It explains the split the rule draws between the names a program is built from and the text a person reads, why the line falls where it does, and how much of it a script can decide.

## Two audiences, two languages

A product built for Brazilian users has two audiences that never meet. The person using it reads screen text, labels, notifications and error messages, and reads them in Portuguese. The people and agents building it read routes, environment variables, column names, CSS classes, test names and commit history, and that audience is not fixed: the next contributor, the library whose error message quotes a field name, the agent loading the repository, the vendor reading a stack trace. English is the language that audience already shares, because it is the language of every keyword, standard library and dependency the names sit beside.

Mixing the two produces the code that triggered this rule. In the Ahrena Console, `/api/sessoes`, `PORTA_CONSOLE` and `buscarSessoes` sat next to `fetch`, `process.env` and `async`. Each name is readable to its author and each is a translation step for everybody else, and a half-translated codebase is worse than either pure one: a reader cannot guess whether the session list is `sessions`, `sessoes` or `listaSessoes`, so every search becomes two.

The user's language does not lose anything by this. It moves to where it belongs — string literals, translation files, templates, the conversation with the person — and stays there in full.

## Why the rule binds the new name, not the old code

The rule asks for a change on a new name even when every name around it is still Portuguese. That is deliberate. A rule that waits for the surrounding code to be clean is a rule that never applies, because the surrounding code is never clean on its own; and a codebase converges on English one change at a time only if each change stops adding to the debt. Renaming what already exists is separate work, owned by an issue in the consuming repository, and the rule does not demand it of a change that only passes by.

That is why the hook is prospective (`--changed`), the same move [`rules/debt-markers.md`](../rules/debt-markers.md) and [`rules/comment-pointers.md`](../rules/comment-pointers.md) make.

## What a script can decide without a dictionary

Telling English from any other language in general needs a dictionary or a model. The predecessor's `lex-commit-language` required English commit subjects and named a commitlint rule that did not exist, and [`contributing/docs/contribution-flow.md`](../../../contributing/docs/contribution-flow.md) refused to restate it for exactly that reason. This rule does not reverse that refusal. The hook decides two narrower states that need neither:

- **A Portuguese diacritic in a name.** `á à â ã é ê í ó ô õ ú ü ç` do not occur in English identifiers. `sessão` and `atençãoAqui` are not ambiguous.
- **A segment on a closed list.** The name is split on camelCase, snake_case, kebab-case, dots and slashes, and each segment is looked up, whole, in a list of Portuguese words that are common in identifiers and are not English words: `sessao`, `porta`, `dados`, `nucleo`, `atencao`, `rotulo`, `titulo`, `usuario`, `buscar`, `salvar` and about a hundred more. Each entry carries its English, which the finding offers.

The list can only miss; it is built so that it never misfires on English. A word that is also English is left off it — `data`, `total`, `valor`, `tempo`, `pasta`, `mural`, `nova`, `real`, `final` — and a segment is matched whole, so `portal` is not `porta`. A Portuguese name made only of unlisted words passes the hook and is the reviewer's.

The other half of the precision is where the hook looks. Screen copy lives in string literals and comments, so both are masked before a line is read and their prose is never a name. What is read is a fixed set of name positions: a declaration after its keyword, a key or member at the start of a line, an assignment where the language declares by assigning, an environment-variable member, a `.env` key, a CSS selector or custom property, a `className` value, an SQL table or column definition, and a string literal whose whole shape is a name — an object or JSON key, a route, a URL path and its parameter names, a CLI option, an `UPPER_SNAKE` variable name. `"Sessões ativas"` is text; `"/api/sessoes"` is a route; the hook tells them apart by shape, not by language.

Measured on this repository in the pull request that added the hook: 340 files read, and no finding outside the hook's own word list and test fixtures. On the fixture modelled on the Console it finds the route, the parameter, the variable, the function, the type member and the directory, and none of the Portuguese screen text beside them.

## The escape hatches, and why each exists

**`ADR-N` on the line.** Some names are not the author's to choose: a field of a government API (`razao_social`), a column of a database the service only reads, a key a partner's webhook sends. Translating them would break the contract. The decision to keep them is real and recorded once in a decision record, and the pointer on the line says so, in the vocabulary [`rules/comment-pointers.md`](../rules/comment-pointers.md) already uses.

**`--exclude <glob>`.** Vendored code and recorded fixtures of such an API cannot carry a comment, and JSON cannot carry one at all. The path is left out of the run instead, where the exclusion is visible in the command line that CI runs.

There is no `--fix`. A rename crosses every file that uses the name, and the English word is a design choice the [`rules/ubiquitous-language.md`](../rules/ubiquitous-language.md) glossary may already have made.

## What a reviewer still owns

- A Portuguese name made of unlisted words (`remessa`, `cobranca`, `boleto` when it is not the domain's own term).
- A name the hook cannot see: a function parameter, a destructured binding, an import alias, a JSX attribute, a name in a language or template the hook does not lex (HTML, Vue, Svelte).
- A test name written as a sentence in a string (`it("deve listar as sessões")`): it is prose the hook deliberately does not read, and it belongs in English because the people who read test output are the backstage audience.
- The commit message and the pull-request title and body. The subject question stays the one `contribution-flow.md` asks, now pointing at this rule.
- A domain term with no English equivalent. `CPF`, `CNPJ`, `Pix` and `boleto` are names of things, and the ubiquitous language keeps them; the rule asks for English words, not for the translation of proper nouns.

## Where this stops

This document covers names and the text around them. It does not choose the user's language — that is the product's decision and may be several languages — and it does not cover how screen text is organised for translation, which is the frontend's concern. Renaming an existing codebase is a migration with its own plan, not a finding of this rule.
