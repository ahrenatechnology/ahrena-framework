# TypeScript exposure and design

Opened by step 4 of `SKILL.md` when the change writes to an exit — a log, a response, an error message, a trace, standard output, a client bundle — or adds a class, a port or a constructor. `docs/sensitive-data.md` and `docs/design.md` argue the corrections.

### TS-20 Something sensitive leaves the layer that owns it

- **Rule:** nothing sensitive leaves the layer that owns it — `ahrena-engineering-security:rules/layer-exposure.md` (issue #294, pull request #301), the language-agnostic exposure rule; until it lands, DAT-1 of `reviewing-sensitive-data` and ACC-8 of `reviewing-access`. This condition is its TypeScript form. Report it as blocking, as the security conditions it stands for are.
- **State:** an exit written with a whole value instead of named fields — `res.json(row)`, `log.info(order)`, `log.error({ err })` on an upstream error, `console.log(config)`, `JSON.stringify(error)`, a spread `{ ...user }` into a response; an upstream error's `message` returned to a caller; a credential, a token, personal data, an access policy, a role or resource identifier, or infrastructure layout in any exit; a secret read in a module the client bundle imports; a type that holds a secret with no redacting `toJSON` and inspect method.
- **Detect:** for each exit the change writes, list the fields that leave. A whole object, an error or a response passed as one value is the finding, whatever it holds today, because its fields change without this line changing. Follow an error from the adapter that caught it to the boundary that answers: if no translation sits between them, the upstream detail crosses.
- **Exempt:** an internal log that holds the `cause` chain of a translated error, provided it holds no secret and the classes above were not in the error; a test's assertion output.
- **Correct:** an allowlist of named fields, typed by the response schema or a `Pick`; a `Secret` wrapper for the value; translation at the adapter, with a generic message and a correlation id to the caller and the detail in `cause` (`docs/sensitive-data.md`).

### TS-21 A pattern from another language, against TypeScript's grain

- **State:** a class of only static methods where a module of functions was meant; an `I`-prefixed interface for every class; a getter and setter pair around a field with no logic; an abstract base class used only to share code; a service locator or a reflection-based container in code that does not use a framework built on one; a boxed type (`String`, `Number`, `Object`) in a signature; overloads that differ only in trailing parameters or in one argument's type.
- **Detect:** read the construct against `docs/design.md` and the TypeScript handbook's Do's and Don'ts it cites. The question is whether TypeScript has a simpler construct for the same intent.
- **Exempt:** a framework that requires the construct (an Angular or NestJS provider, a class a library expects to extend).
- **Correct:** a module of functions; an interface named for what it is, declared by its consumer; a public `readonly` field; a function the subclasses would have called; constructor injection from the composition root; `string`, `number`, `object`; one signature with optional parameters or a union.

### TS-22 A concrete collaborator where a port was meant

- **State:** a module in the application or domain layer that imports an adapter — a database client, an HTTP client, an SDK — and calls it, instead of receiving a port; a class that constructs its own collaborators with `new` inside its methods.
- **Detect:** read the imports of each changed application or domain module. This is condition 6 of `ahrena-engineering-fundamentals:rules/solid.md` in TypeScript's form, gated by the abstraction trigger of `rules/yagni.md` as that rule states: report it when the trigger is met, not before.
- **Exempt:** a value object or a pure function from another domain module; a composition root, whose job is constructing adapters.
- **Correct:** declare the port beside the code that needs it as a structural interface, take it as a parameter or a constructor argument, and construct the adapter in `main.ts` (`docs/design.md`).
