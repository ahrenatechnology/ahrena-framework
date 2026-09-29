# ADR-012: The repository's issue templates first, and Ahrena's forms by default

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #110

## Context

The survey in #45 counted the predecessor's `.github/ISSUE_TEMPLATE/`, 1,015
lines of GitHub issue forms, and called them "the real schema of a well-formed
issue": epic, feature request, API user story, frontend user story, tech task,
plan, bug, and the form chooser's `config.yml`. #39 set them aside, and
`issue-quality.md` said a template "is not required". That cut threw out the
structure along with the configuration it was tangled with: the labels, the
project board, the default assignee and the `status: todo` label that the
state vocabulary (#80) owns.

The owner's direction on 2026-09-28 came in three steps. First: backlogs arrive
as epics, and the framework should propose the stories, tasks, spikes and
bugs under them, each structured as the templates are. Second, on a first
attempt that wrote new Markdown templates from scratch: take the original
Ahrena's issue templates instead, make them Ahrena's templates, and make them
replicable into the projects that install the framework. Third: when an issue
is created, read the repository; if it has its own issue template, create the
issue from it, and if not, apply the default, which is the templates Ahrena
already has.

That is the rule this framework follows for stacks (`ADR-008`) and plans
(`ADR-011`): what the project and its forge provide comes first, and the
framework supplies what they do not.

## Decision

An issue is written from a template of its type. The repository's own
template in `.github/ISSUE_TEMPLATE/` is used when it has one for that type.
Where it has none, Ahrena's default is used.

Ahrena's defaults are the predecessor's issue forms, adapted and nothing more.
The Guardia-specific parts go: the project board, the default assignee, the
contact links, the Slack and email fields, and the company's media type,
headers and documentation links in the API story. The labels go as well,
including `status: todo`, because labels are each project's configuration. What
this framework's rules read is added to every form: an `Acceptance criteria`
field in the shape of `ADR-007`, and a `Left to other issues` field. One new
form is added, the spike, which the predecessor did not have. The forms are
shipped in `skills/opening-issues/references/issue-forms/`.

An issue's body is written the way GitHub renders a filled-in form: each field
as a `### <label>` section, in the form's order. An issue written by an agent
and one filed by hand therefore read alike. When a repository's own template
has no acceptance criteria, the section is added after its last field, because
`traceability.md` reads it. Nothing else in the repository's template is
changed.

The native issue type is the one the template names, or the nearest the
organisation has. The forms can also be installed into a repository, so the
same forms appear to people filing by hand.

## Consequences

The forms are the single source, and the agent's guides are derived from them.
Each `references/<type>.md` is generated from its form by
`scripts/render_issue_forms.py`: the sections in order, with the form's own
descriptions and examples as the guidance. CI runs the script in check mode, so
a form edited without regenerating its guide fails. The script reads the
forms with a small YAML reader of its own. The framework takes no dependency
beyond the standard library, and CI installs nothing. Before it shipped, its
output was checked against PyYAML's for all nine forms, and they matched.

`skills/installing-issue-forms`, run by `/install-issue-forms`, copies the
forms into a repository. It adds only the types the repository lacks, never
overwrites a form it already has, matches each form's type to the
organisation's, and lands through a pull request like any change. Agents do
not need it, because they read the defaults directly.

The user stories keep the predecessor's Gherkin scenarios (happy path,
corner cases, errors), and their `Acceptance criteria` field numbers those
scenarios, one `AC-n` line each, so a test can name them. That states each
criterion twice: once as a scenario, and once as a one-line index entry. The
trace needs the numbered line, and the scenarios are what a reviewer reads, so
both stay.

The organisation has three native types: `Task`, `Bug` and `Feature`. The
epic form names `Epic`, which it lacks. When the forms are installed, or an
issue is created, the nearest type is used. An organisation that adds `Epic`
or `Spike` as types gets the exact one with nothing to change.

`issue-quality.md` keeps its three conditions. Its paragraph on templates
changes: a template is how an issue meets them, not a substitute for them.

## Alternatives considered

- **New templates written for this framework.** This was the first attempt
  (#111's first version), and the owner rejected it. The predecessor's forms
  are the ones people already know, they are GitHub's native format, and they
  can be installed as they are.
- **Ahrena's forms always, over the repository's own.** Rejected by the owner.
  A project's own templates encode its way of working. The framework adds
  what the trace needs to them, and replaces nothing.
- **Guides written by hand beside the forms.** Rejected, because they would be
  a second copy of each form that drifts from it. They are generated instead,
  and CI checks they are current.
- **Keep the labels.** Rejected. `status: todo` is the state vocabulary, and
  the kind labels, `bug report 🐞` or `evolvability ♻️`, are the predecessor's
  project's names. Both are configuration (#80). The forms still carry the
  native issue type, which the forge provides.
