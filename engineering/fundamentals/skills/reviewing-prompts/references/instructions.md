# Instructions

Opened by step 1 of `SKILL.md` for every route of this skill: an instruction file, a prompt template, a prompt built in code, and the body of an agent, skill or command definition.

Each condition gives the state, how it is detected, what exempts it and the correction. The correction is always replacement text in the finding, never a request to clarify.

## What the reader is told

### PRM-1 Two instructions that cannot both be followed

- **State:** two sentences, in this text or between it and another instruction file in force, that give opposite directions for one situation: "always ask before editing" and "make the change without asking", a length limit and a required list of sections that exceeds it.
- **Detect:** list every imperative in the changed text. For each one the change added or edited, search the rest of the text and the other files from step 2 for an instruction on the same situation.
- **Exempt:** a general instruction and a specific exception, when the text says which wins.
- **Correct:** delete one, or state the precedence in the sentence itself.

### PRM-2 A rule with no reason and no boundary

- **State:** an instruction stated as an absolute with nothing saying what it protects: "never use X", "always do Y". The reader cannot tell the cases it was written for from the ones it was not, so it either over-applies the rule or drops it under pressure from the task.
- **Detect:** for each absolute the change added, look for the reason in the same paragraph.
- **Exempt:** a hard constraint whose reason is self-evident and that has no sensible exception, such as an output format a parser requires.
- **Correct:** add the reason in one clause, and the case where the rule does not hold when there is one.

### PRM-3 Emphasis doing the work of explanation

- **State:** capitals, repeated warnings or escalating words carrying an instruction: "IMPORTANT", "YOU MUST", "under NO circumstances", the same rule stated three times. A capable reader over-applies an instruction written this way, and when everything is marked critical nothing is.
- **Detect:** search the added lines for capitalised imperatives and for a rule repeated in different words.
- **Exempt:** one marker on the one constraint whose violation is costly and that a test showed was being missed.
- **Correct:** state it once, plainly, with its reason.

### PRM-4 A term the reader was never given

- **State:** a name, an abbreviation or a label used as if known: a project codename, "the standard format", "the usual checks", an identifier coined in the conversation that produced the prompt.
- **Detect:** the marks from step 3.
- **Exempt:** a term defined in a file the reader is certain to hold, per step 2.
- **Correct:** replace the term with what it stands for, or define it at first use.

### PRM-5 A quantity word where a threshold belongs

- **State:** "brief", "a few", "large", "when appropriate", "if needed", "as necessary" at a point where the reader has to decide something.
- **Detect:** search the added lines for quantity and discretion words attached to an action.
- **Exempt:** a case where any reasonable reading gives an acceptable result.
- **Correct:** state the number, the limit or the condition: "at most three sentences", "when the file is over 500 lines".

### PRM-6 An example the reader will copy

- **State:** a single example, or several that share an incidental feature, beside an instruction that is meant more generally. The reader reproduces the example's length, wording and structure.
- **Detect:** for each example the change added, compare its incidental features with what the instruction intends. Read any output samples for that feature recurring.
- **Exempt:** an example labelled as one of several shapes, or a format that is meant to be reproduced exactly.
- **Correct:** describe the quality wanted in prose, give several examples that differ from each other, and say they are illustrative.

### PRM-7 An example that contradicts its instruction

- **State:** the text says one thing and its example does another. The reader follows the example.
- **Detect:** read each example against the sentence it illustrates.
- **Exempt:** none.
- **Correct:** fix whichever is wrong, and say in the finding which the surrounding text supports.

## What the reader is not told

### PRM-8 The task with no purpose and no finish

- **State:** an instruction to do something with no statement of what it is for or what done looks like. The reader stops early or never stops.
- **Detect:** ask of the text: what is the result for, and what would make the reader stop? Neither answer on the page is the state.
- **Exempt:** a prompt for a single transformation whose output is its own finish, such as a translation.
- **Correct:** add one sentence for the purpose and one for the stopping condition.

### PRM-9 A command for one case where a principle was needed

- **State:** a narrow instruction added to fix one observed failure, such as a rule naming one phrase or one input, where the underlying behaviour was wider. It fixes that case and leaves its neighbours.
- **Detect:** read the pull request's description for the failure that prompted the change, and ask what general behaviour it was an instance of.
- **Exempt:** a case that is unique.
- **Correct:** describe the situation and the concern, so the reader can decide the neighbouring cases too.

### PRM-10 Words spent where the reader needs none

- **State:** sentences telling the reader to be careful, thorough, accurate or helpful, or a generic role line standing in for instruction, while the hard judgment of the task gets a sentence or none.
- **Detect:** mark each sentence a capable reader would follow without being told. Then find where a newcomer to this task would most likely go wrong, and count what the text spends there.
- **Exempt:** a role or audience line that changes the output, such as who the reader's answer is for.
- **Correct:** delete the generic sentences and write the paragraph the hard judgment needs.

### PRM-11 A constraint the change removed

- **State:** a constraint, a stopping condition, a reason or a boundary present in the base version and absent from the new one, with nothing in the description saying why.
- **Detect:** step 5.
- **Exempt:** a removal the description or the issue explains.
- **Correct:** restore the sentence, or the finding is a **question** naming it.

## How the page is built

### PRM-12 Always-loaded text that is needed rarely

- **State:** material added to a file that enters every request, such as `CLAUDE.md` or `AGENTS.md`, that applies to one kind of task: a procedure, a reference table, a long example.
- **Detect:** for each added block, ask what fraction of requests need it. Count its lines.
- **Exempt:** a fact every task needs, such as how to run the tests.
- **Correct:** move the block to a file that is loaded on demand and leave one line saying when to open it.

### PRM-13 Instructions and data in one undivided string

- **State:** a prompt built in code where interpolated material, such as a document, a record or a user's message, sits among the instructions with nothing marking where it starts and ends.
- **Detect:** the reconstructed text from step 2. Ask whether the reader could tell the author's sentences from the inserted ones.
- **Exempt:** a short interpolated value from a closed set.
- **Correct:** put each kind of material in its own labelled block, and the instructions outside them. That outside text can also address the model is LLM-1 in `skills/reviewing-model-use/SKILL.md`.

### PRM-14 A format the instruction asks against

- **State:** the prompt asks for output in one shape while being written in another, or forbids a format by naming it and not the one wanted: "do not use markdown" in a prompt that is itself all bullets.
- **Detect:** compare the style of the prompt with the style of output it asks for. Search for negative format instructions.
- **Exempt:** a prompt whose output is parsed and whose format is given as a schema.
- **Correct:** state the wanted format positively, and write the prompt in the register it asks for.

### PRM-15 A reference to something outside the page

- **State:** "as discussed", "the previous approach", "see the thread", "the file from earlier", or a path that does not exist at the head of the change.
- **Detect:** search for references to conversation and history. Resolve every path and tool name the text mentions against the tree and the reader's tools.
- **Exempt:** none. The reader has the page.
- **Correct:** put the content the reference stood for on the page, or correct the path.
