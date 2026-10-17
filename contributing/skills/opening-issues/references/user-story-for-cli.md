<!-- Generated from issue-forms/user-story-for-cli.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# CLI User Story

Template for a command-line (CLI/TUI) user story: acceptance criteria and the entrypoint's surface — command, arguments, I/O and exit codes.

Native issue type: `User Story`. Title: `{{ summarize the user story here }}`.

Fill in the fields below to register a user story whose delivery surface is a command-line entrypoint. Use this instead of the API story when the capability is run as a command, not called over HTTP.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### As a (user role / persona)

Who runs the command?

For example:

> e.g. a release engineer

Required.

### I want (specific objective)

What does the persona want the command to do?

For example:

> e.g. convert an amount between two currencies at a given rate

Required.

### So that (benefit and value)

What is the benefit or value?

For example:

> e.g. I get the equivalent value without opening a spreadsheet

Required.

### Happy Path Scenario

Success scenario in Gherkin format, phrased as running the command

Starts as:

```markdown
```gherkin
Scenario: {success_scenario_name}
  Given {pre_condition}
  When I run `{command} {args}`
  Then stdout is {expected_output}
  And the exit code is 0
```
```

Required.

### Corner Cases

Edge case scenarios in Gherkin format

Starts as:

```markdown
```gherkin
Scenario: {edge_case_name}
  Given {pre_condition}
  When I run `{command} {args}`
  Then stdout is {expected_output}
```
```

Optional.

### Error Cases

Error scenarios — bad input or a rejected operation

Starts as:

```markdown
```gherkin
Scenario: {error_scenario_name}
  Given {error_pre_condition}
  When I run `{command} {bad_args}`
  Then stderr contains {error_message}
  And the exit code is non-zero
  And stdout is empty
```
```

Optional.

### Acceptance criteria

Number the scenarios above, one line each: AC-1, AC-2 and upward, never renumbered. A test names the one it covers as #<issue>/AC-<n>.

Starts as:

```markdown
- AC-1: <happy path scenario, in one line>
- AC-2: <corner case>
- AC-3: <error case>
```

Required.

### Left to other issues

Decisions already made, work blocked elsewhere, and parts another issue owns, each by number.

Optional.

### Command

The command as invoked, with its positional arguments.

For example:

> convert <amount> <from> <to> <rate>

Required.

### Arguments and options

Each positional argument and option, its type and whether it is required.

Starts as:

```markdown
| Name   | Kind       | Type   | Required | Description  |
|--------|------------|--------|----------|--------------|
| amount | positional | string | yes      | description  |
| --flag | option     | bool   | no       | description  |
```

Optional.

### Input / output / exit codes

What the command reads, what it writes to stdout/stderr, and the exit codes it returns.

Starts as:

```markdown
- **stdin:** {what it reads, or "none"}
- **stdout (success):** {what it prints}
- **stderr (error):** {the message shape}
- **exit codes:** 0 success; non-zero on {error condition}
```

Required.

### Examples

Concrete invocations and their output.

Starts as:

```markdown
```console
$ {command} {args}
{expected_output}
```
```

Optional.

### Metrics

Any usage, success-rate or performance metric worth collecting (optional for a CLI).

Starts as:

```markdown
- {metric_1}
- {metric_2}
```

Optional.

### References

Links to relevant documentation

Starts as:

```markdown
- [Product documentation](https://docs.example.com/)
- {additional_reference}
```

Optional.

## Objective (User Story)

## Acceptance Criteria

## CLI Surface

## Metrics

## References
