---
id: sensitive-data
type: doc
clade: engineering
subclade: typescript
title: Keeping sensitive data in its layer, in TypeScript
summary: How TypeScript code keeps a credential, personal data, an access policy, a resource identifier, infrastructure layout or a whole configuration, error or upstream response out of every output, log, trace, error message and response - an allowlist of fields at every exit, a redacting representation for a type that carries a secret, a logger given named fields, an error translated before it crosses a boundary, and nothing secret in a client bundle.
references:
  - docs/error-handling.md
  - docs/libraries.md
---

# Keeping sensitive data in its layer, in TypeScript

**Nothing sensitive leaves the layer that owns it.** The rule is language-agnostic and belongs to the security plugin: `engineering/security/rules/layer-exposure.md`, proposed in pull request #301 for issue #294; its origin is an application built by this agency that printed AWS IAM policies to its output, which neither the review nor the security guardian reported. Until that rule lands, the security disciplines' conditions that already exist apply — DAT-1 of `reviewing-sensitive-data` (personal data, payment data, a credential, a session token, a whole request or response body) and ACC-8 of `reviewing-access` (an error that returns a stack trace or a query). This page says how TypeScript code holds the rule: what is written, and what is never written, so that the property holds from the first line rather than being found at review.

The sensitive classes are those #294 names: a credential or token, personal data, an access policy or role, a resource identifier (an ARN, an account or subscription id), infrastructure layout (hosts, networks, a plan or a state), and a whole configuration, error or upstream response. The exits are every place a value leaves the unit: a return value that crosses a boundary, an HTTP response, a log line, a trace attribute, an error message, a metric label, standard output, and a client bundle.

## An exit is an allowlist of fields

What a unit emits is a list of named fields, built on purpose. `res.json(order)` returns every field the `Order` row has today and every one a migration adds tomorrow; `res.json({ id: order.id, status: order.status, total: order.total })` returns three. The same holds for a log line and an error.

In TypeScript the allowlist is a type: the response's schema ([`rules/runtime-validation.md`](../rules/runtime-validation.md) applies on the way out as on the way in), or a `Pick<Order, "id" | "status" | "total">` built field by field. A spread — `{ ...order, total }` — is not an allowlist, because it carries whatever the source carries.

## A type that carries a secret redacts itself

A value that holds a credential, a token or personal data is wrapped in a class whose every representation is redacted, so that the accident of passing it to `JSON.stringify` or a logger writes nothing:

```ts
class Secret {
  readonly #value: string;
  constructor(value: string) { this.#value = value; }
  reveal(): string { return this.#value; }
  toJSON(): string { return "[redacted]"; }
  [Symbol.for("nodejs.util.inspect.custom")](): string { return "Secret([redacted])"; }
}
```

The field is an ECMAScript private name (ECMA-262 §15.7, `#value`), which no reflection or spread can read, unlike TypeScript's `private`, which is erased. `JSON.stringify` calls `toJSON` when it is present (ECMA-262 §25.5.4.2, SerializeJSONProperty), and Node's `util.inspect` — which `console.log` uses — calls the `nodejs.util.inspect.custom` method; this plugin checked both on Node 26. The secret is read only by `reveal()`, at the one call that needs it.

## A logger is given named fields, never an object

pino, which [`libraries.md`](libraries.md) recommends, takes a fields object and a message: `log.info({ orderId: order.id, status: order.status }, "order placed")`. Never `log.info(order)`, `log.info({ order })`, `log.error(error)` with an upstream error, or `console.log(config)`. pino's `redact` option names paths that are replaced with `[Redacted]` in every line, and it is set for the paths a request carries — `req.headers.authorization`, `req.headers.cookie` — as a second line of defence behind the allowlist, not instead of it.

A trace attribute and a metric label are held the same way: named, chosen, and never a whole object or a raw identifier the classes above include.

## An error is translated before it crosses a boundary

An upstream error — a cloud SDK's, a database driver's, another service's — carries its request, its resource identifiers and sometimes the policy that refused it. It is caught at the adapter that called upstream and translated into this program's own error, with a message that says what failed in this program's terms, and the upstream error kept in `cause` (ECMA-262 §20.5.8.1, InstallErrorCause) for the internal log only. At the outer boundary ([`error-handling.md`](error-handling.md)), the caller receives a generic message and a correlation id; the detail, from `cause`, goes to an internal log that itself holds no secret. Returning `error.message` from an upstream error, or `JSON.stringify(error)`, to a caller is the pass-through #294 was opened for.

## Nothing secret reaches a client bundle

Code that runs in a browser ships to every visitor. A bundler inlines the environment variables the code reads, so a server-side secret read from a module that the client imports is published. Secrets are read only in server modules, through the configuration parsed at startup ([`libraries.md`](libraries.md), "Configuration"), and a value meant for the client is exposed through the framework's own public-variable mechanism, by name, never by passing the configuration object. The frontend clade owns how its framework separates the two.

## Where this stops

**The rule and its detector are #294's.** That issue gives the closed list of classes and exits, and a hook for the clearest cases; this page is the TypeScript form, and `reviewing-typescript` holds the language's part of it as TS-20. When pull request #301 lands, the rule's path above becomes a link, and this page changes only that sentence.

**An allowlist is not an access check.** Who may read a field at all is `reviewing-access`; this page is about the field not leaving by accident once read.

**Redaction is not encryption.** A `Secret` wrapper keeps a value out of a log; storing it is `reviewing-sensitive-data`'s cryptographic conditions.

## Sources

- Issue #294 of this repository: the rule, its sensitive classes and exits.
- ECMA-262, 17th edition (ES2026): §15.7 Class Definitions (private names); §25.5.4 JSON.stringify and §25.5.4.2 SerializeJSONProperty (`toJSON`); §20.5.8.1 InstallErrorCause. <https://262.ecma-international.org/17.0/>
- Node.js, `util.inspect.custom`: <https://nodejs.org/api/util.html#utilinspectcustom>.
- pino, `redact`: <https://github.com/pinojs/pino/blob/main/docs/redaction.md>.
- MDN, `Error` `cause`: <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/Error>.
