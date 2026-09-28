# User story

A behaviour a user can see, delivered by one pull request. Native type: `User Story` or `Story` if the organisation has it, otherwise `Feature`.

Title: what the user can now do. "Pay an invoice by bank transfer".

```markdown
## Story

**As** <who>,
**I want** <what they can do>,
**so that** <the value it gives them>.

## Why

The evidence behind the story: the request, the measurement, the support
ticket. Where there is none, say so.

## Acceptance criteria

- AC-1: Given <state>, when <action>, then <observable outcome>.
- AC-2: Given <edge case>, when <action>, then <outcome>.
- AC-3: Given <failure>, when <action>, then <error the user sees, and what is logged>.

## Interface

Only when the story changes one. For an API: method, path, request and
response shape, error codes. For a screen: its states, including empty,
loading and error. Put a contract or a schema in the repository and link it
rather than pasting it here.

## Left to other issues

- <what this story does not cover, each by number>
```

Every criterion is written so a test can decide it, and the test names it as `#<issue>/AC-<n>` (`writing-acceptance-criteria`). Cover the happy path, at least one edge, and at least one failure. A story whose only criteria are happy paths has not been thought through.
