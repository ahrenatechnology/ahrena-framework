// athena.workflow.js — the Claude Code Workflow binding for the agency.
//
// This is a REFERENCE, not run by CI. It illustrates how Athena's orchestration
// loop maps onto the Claude Code Workflow API: a deterministic JS fan-out that
// spawns one subagent PER TEST STEP, so the Workflow panel shows each stage and
// each red→green test step as its own row rather than a coarse "build frontend".
//
// The shape it encodes is the portable spec (skills/orchestrating-delivery):
//   ensure the issue (find-or-create) -> plan it -> for each routed layer, run
//   that builder's test-step arc
//   (mirroring the clade's testing skill) then the Argos<=3 review loop -> stack.
// It writes no production code itself; every agent() call delegates to a
// specialist — Iris/Apollo/Clio for the steps, Argos/Erodos for the loop —
// exactly as Athena does.
//
// Per-builder arcs mirrored here:
//   Iris   -> testing-frontend          (wireframe, components, state, contract)
//   Apollo -> driving-with-tdd + specifying-with-bdd (domain, use case, oltp, api)
//   Clio   -> testing-data              (schema, medallion, expectations, marts)
//
// CODEX CAVEAT: Codex's agents.max_depth default is 1. Athena spawning a step
// agent is already depth 1, so a build agent that spawned these step agents
// itself would be depth 2 and exceed the default. On the Codex binding the
// manager (Athena) therefore spawns these step agents DIRECTLY — the fan-out is
// flattened, exactly as this script spawns them from the top level — rather than
// Iris/Apollo/Clio sub-spawning. Raising max_depth to 2 is the owner's opt-in.
//
// Pass the plan's layers as `args.layers`, each { clade, dependsOn }, and the
// issue as `args.issue` so BDD scenarios can name #<issue>/AC-n.

export const meta = {
  name: 'athena-delivery',
  description: "Athena's loop: plan, then per routed layer run the builder's test-step arc + Argos<=3 loop, then stack",
  phases: [
    { title: 'Plan', detail: 'ensure the issue (find-or-create), then decompose it into typed, ordered, routed layers' },
    { title: 'Iris · Wireframe', detail: 'designer + Playwright e2e skeleton (red)' },
    { title: 'Iris · Components', detail: 'storybook, snapshot, visual regression, axe' },
    { title: 'Iris · State', detail: 'interaction + unit' },
    { title: 'Iris · Contract', detail: 'e2e green + page axe' },
    { title: 'Apollo · Domain', detail: 'TDD unit (red)' },
    { title: 'Apollo · Use case', detail: 'test doubles' },
    { title: 'Apollo · OLTP', detail: 'integration + migrations' },
    { title: 'Apollo · API', detail: 'BDD acceptance + consumer contract' },
    { title: 'Clio · Schema', detail: 'contract (red)' },
    { title: 'Clio · Medallion', detail: 'transform unit' },
    { title: 'Clio · Expectations', detail: 'freshness + uniqueness' },
    { title: 'Clio · Marts', detail: 'contract + reconciliation' },
    { title: 'Stack', detail: 'open the reviewed layers as a stack, lowest-first' },
  ],
}

// --- schemas: every delegated agent returns test state, not prose -----------

// One test step's outcome, so the expanded panel row reads e.g.
// "e2e skeleton — red (expected)" / "snapshot — green (12 passed)".
const STEP_SCHEMA = {
  type: 'object',
  properties: {
    lane: { type: 'string' }, // the test lane, e.g. 'e2e', 'unit', 'expectations'
    status: { type: 'string', enum: ['red', 'green'] },
    counts: {
      type: 'object',
      properties: { passed: { type: 'integer' }, failed: { type: 'integer' } },
    },
  },
  required: ['lane', 'status'],
}

const ISSUE_SCHEMA = {
  type: 'object',
  properties: {
    issue: { type: 'string' }, // the number the branch and every PR carry
    opened: { type: 'boolean' }, // true when opening-issues created it
  },
  required: ['issue'],
}

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    layers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          clade: { type: 'string', enum: ['frontend', 'backend', 'data'] },
          dependsOn: { type: 'array', items: { type: 'string' } },
        },
        required: ['clade'],
      },
    },
  },
  required: ['layers'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    clean: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['clean', 'findings'],
}

const MAX_ROUNDS = 3 // the loop cap from orchestrating-delivery step 5

// --- the per-builder test-step arcs -----------------------------------------
//
// Each builder is a sequence of layer-phases. Each layer-phase is an ordered
// list of "rungs"; a rung's steps run in parallel (independent concerns), and
// the rungs themselves run in order. `expect` is the lane's expected status, so
// a red skeleton reads as "red (expected)" rather than a failure. `who` names
// the tool the testing skill drives, and `id` is the panel-row label.

const BUILDERS = {
  frontend: {
    agent: 'Iris',
    skill: 'testing-frontend',
    layers: [
      {
        key: 'iris:wireframe',
        phase: 'Iris · Wireframe',
        rungs: [
          [{ id: 'iris:wireframe:design', lane: 'design', who: 'Designer', expect: 'green' }],
          [{ id: 'iris:wireframe:e2e-skeleton', lane: 'e2e', who: 'Playwright', expect: 'red' }],
        ],
      },
      {
        key: 'iris:components',
        phase: 'Iris · Components',
        rungs: [
          [{ id: 'iris:components:storybook', lane: 'story', who: 'Storybook', expect: 'green' }],
          [
            { id: 'iris:components:snapshot', lane: 'snapshot', who: 'Jest', expect: 'green' },
            { id: 'iris:components:visual-regression', lane: 'visual', who: 'Chromatic', expect: 'green' },
            { id: 'iris:components:axe', lane: 'a11y', who: 'axe', expect: 'green' },
          ],
        ],
      },
      {
        key: 'iris:state',
        phase: 'Iris · State',
        rungs: [
          [
            { id: 'iris:state:interaction', lane: 'interaction', who: 'Testing Library', expect: 'green' },
            { id: 'iris:state:unit', lane: 'unit', who: 'Vitest', expect: 'green' },
          ],
        ],
      },
      {
        key: 'iris:contract',
        phase: 'Iris · Contract',
        rungs: [
          [
            { id: 'iris:contract:e2e-green', lane: 'e2e', who: 'Playwright', expect: 'green' },
            { id: 'iris:contract:page-axe', lane: 'a11y', who: 'axe', expect: 'green' },
          ],
        ],
      },
    ],
  },
  backend: {
    agent: 'Apollo',
    skill: 'driving-with-tdd + specifying-with-bdd',
    layers: [
      {
        key: 'apollo:domain',
        phase: 'Apollo · Domain',
        rungs: [[{ id: 'apollo:domain:tdd-unit-red', lane: 'unit', who: 'TDD', expect: 'red' }]],
      },
      {
        key: 'apollo:usecase',
        phase: 'Apollo · Use case',
        rungs: [[{ id: 'apollo:usecase:doubles', lane: 'unit', who: 'test doubles', expect: 'green' }]],
      },
      {
        key: 'apollo:oltp',
        phase: 'Apollo · OLTP',
        rungs: [
          [
            { id: 'apollo:oltp:integration', lane: 'integration', who: 'Testcontainers', expect: 'green' },
            { id: 'apollo:oltp:migrations', lane: 'migration', who: 'migration runner', expect: 'green' },
          ],
        ],
      },
      {
        key: 'apollo:api',
        phase: 'Apollo · API',
        rungs: [
          [
            { id: 'apollo:api:bdd-acceptance', lane: 'acceptance', who: 'BDD', expect: 'green', bdd: true },
            { id: 'apollo:api:contract-consumer', lane: 'contract', who: 'Pact', expect: 'green' },
          ],
        ],
      },
    ],
  },
  data: {
    agent: 'Clio',
    skill: 'testing-data',
    layers: [
      {
        key: 'clio:schema',
        phase: 'Clio · Schema',
        rungs: [[{ id: 'clio:schema:contract-red', lane: 'contract', who: 'schema contract', expect: 'red' }]],
      },
      {
        key: 'clio:medallion',
        phase: 'Clio · Medallion',
        rungs: [[{ id: 'clio:medallion:transform-unit', lane: 'workbench', who: 'dbt test', expect: 'green' }]],
      },
      {
        key: 'clio:expectations',
        phase: 'Clio · Expectations',
        rungs: [
          [
            { id: 'clio:expectations:freshness', lane: 'freshness', who: 'Great Expectations', expect: 'green' },
            { id: 'clio:expectations:uniqueness', lane: 'uniqueness', who: 'Great Expectations', expect: 'green' },
          ],
        ],
      },
      {
        key: 'clio:marts',
        phase: 'Clio · Marts',
        rungs: [
          [
            { id: 'clio:marts:contract', lane: 'contract', who: 'mart contract', expect: 'green' },
            { id: 'clio:marts:reconciliation', lane: 'reconciliation', who: 'recon check', expect: 'green' },
          ],
        ],
      },
    ],
  },
}

// --- 1. Ensure the issue exists, then plan it into routed layers ------------

phase('Plan')

// Issue-first: the branch and every PR carry the issue number, so the issue
// precedes the plan. Athena takes the received issue, or opens one via
// opening-issues (find-or-create) when work arrived without — before planning.
const received = args && args.issue ? args.issue : null
const ensured = await agent(
  received
    ? `Confirm issue ${received} owns this work via opening-issues, then return its number.`
    : `No issue received: open one via opening-issues (find-or-create), then return its number.`,
  { label: 'athena:issue:ensure', phase: 'Plan', schema: ISSUE_SCHEMA },
)
const issue = (ensured && ensured.issue) || received || '(none supplied)'

let planned = args && Array.isArray(args.layers) ? args.layers : null
if (!planned) {
  const result = await agent(
    `Plan issue ${issue} into typed layers via planning-changes and route each via routing-concern. ` +
      `Return one layer per routed clade.`,
    { label: 'plan + route', phase: 'Plan', schema: PLAN_SCHEMA },
  )
  planned = result ? result.layers : []
}
// The routed clades present, in data→backend→frontend dependency order (lowest of
// the stack first). In a real run the code graph's deps decide the order; here the
// convention stands in for it.
const ORDER = ['data', 'backend', 'frontend']
const activeClades = ORDER.filter((c) => planned.some((l) => l.clade === c))
log(`routed clades: ${activeClades.join(', ') || 'none'}`)

// Flatten every active builder's layer-phases into one ordered work-list. Each
// item is one layer-phase; pipeline() runs it through build-steps then the loop.
const workList = activeClades.flatMap((clade) =>
  BUILDERS[clade].layers.map((layer) => ({ clade, builder: BUILDERS[clade].agent, ...layer })),
)

// --- 2. Per layer: run the test-step arc, then the Argos<=3 loop -------------
//
// One agent() per test step keeps each red→green step its own panel row. Steps
// in a rung run via parallel() (independent concerns); rungs run in order. phase
// is set explicitly on every agent() so the groups do not race on the global
// phase() state inside the fan-out.

async function stepArcStage(layer) {
  const steps = []
  for (const rung of layer.rungs) {
    const rungResults = await parallel(
      rung.map((step) => () => {
        const bdd = step.bdd
          ? ` Each scenario names #${issue}/AC-n so the acceptance maps to a criterion.`
          : ''
        return agent(
          `${layer.builder} (${BUILDERS[layer.clade].skill}): drive the ${step.lane} lane with ` +
            `${step.who} for "${layer.key}". Expected end state: ${step.expect}.${bdd} ` +
            `Return {lane, status, counts}.`,
          { label: step.id, phase: layer.phase, schema: STEP_SCHEMA },
        )
      }),
    )
    rung.forEach((step, i) => steps.push({ id: step.id, expect: step.expect, result: rungResults[i] }))
  }
  return { layer, steps }
}

// Argos reviews the layer's working diff, Erodos applies the mechanically
// applicable findings, for at most MAX_ROUNDS rounds. A layer still failing after
// the cap is an escalation, not a fourth round.
async function argosLoopStage(built, layer) {
  const key = layer.key
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    const review = await agent(
      `Argos: review the working diff for layer "${key}" (${built.steps.length} test steps). ` +
        `Return clean + findings.`,
      { label: `argos:review:${key} r${round}`, phase: layer.phase, schema: REVIEW_SCHEMA },
    )
    if (!review || review.clean) {
      return { layer: key, phase: layer.phase, opened: true, rounds: round, steps: built.steps }
    }
    if (round === MAX_ROUNDS) {
      return { layer: key, phase: layer.phase, opened: false, escalated: true, reason: review.findings }
    }
    await agent(
      `Erodos: apply the mechanically applicable findings for "${key}", then have ${layer.builder} ` +
        `re-run the affected lanes. Return the lanes back to green.`,
      { label: `erodos:fix:${key} r${round}`, phase: layer.phase, schema: STEP_SCHEMA },
    )
  }
  return { layer: key, phase: layer.phase, opened: false, escalated: true, reason: 'loop exhausted' }
}

// pipeline() runs each ordered layer through the step arc then the loop, with no
// barrier between stages — a later layer can be in its step arc while an earlier
// one is in review. The stack ordering is reapplied at the end.
const results = (await pipeline(workList, stepArcStage, argosLoopStage)).filter(Boolean)

// --- 3. Stack the reviewed layers, lowest-first -----------------------------

phase('Stack')

const openable = results.filter((r) => r.opened)
const escalations = results.filter((r) => r.escalated)
if (escalations.length) {
  log(`${escalations.length} layer(s) escalated to a human; not stacking those`)
}

const stacked = await agent(
  `Open these reviewed layers as a stack via stacking-pull-requests, each based on the one below, ` +
    `landing lowest-first: ${JSON.stringify(openable.map((r) => r.layer))}.`,
  { label: 'stack the layers', phase: 'Stack' },
)

// The orchestration record Athena hands back: each layer, its test steps and
// rounds, which escalated and why, and the stack result.
return { layers: results, stacked, escalations }
