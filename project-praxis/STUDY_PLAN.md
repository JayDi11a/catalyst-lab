# Praxis Study Plan — Preparing for Coblenz

4 days, ~2-3 hours each. Each day builds on the previous.
After each day you should be able to explain that layer
without looking at notes.

## What Coblenz Will Care About

His group sits at usable PL + formal verification. They'll ask:

1. **"What are you actually proving?"** — They want the precise
   property statements, not hand-waves. Know the ensures clauses.
2. **"Why these properties?"** — What threat model justifies
   these specific invariants? Why is string equality the right
   notion of identity, not semantic similarity?
3. **"What's the trusted computing base?"** — What do you NOT
   verify? Where are the assumptions? They respect honest gaps
   more than overclaims.
4. **"Could a developer actually use this?"** — Usable PL lens.
   How much does an agent developer need to understand about
   F* to benefit from Praxis?

---

## Day 1: The Threat Model and the Pipeline Shape

**Goal**: Explain the hallucination persistence loop problem
and the pipeline that solves it without touching F* syntax.

### Study

Read nothing today except this:

- `tests/praxis/gateway_client.py` lines 522-574
  (PraxisGatewayClient.verify_write)

That's 50 lines. It's the whole pipeline in Python. Read it
until you can answer these from memory:

### Practice Questions (answer out loud)

1. "What is a hallucination persistence loop?"

   Your answer should include: agent hallucinates → stores in
   memory → reads it back next turn → treats it as established
   fact → reasons from it → stores more fabrications →
   compounding error across turns.

2. "Walk me through what happens when an agent tries to write
   to memory."

   Your answer should include the 5 checks IN ORDER:
   - P1: Is the inference chain well-formed? (grounded in
     observations, each step semantically valid)
   - P2: Does this contradict existing memory?
   - P3: Is the content free of injection patterns?
   - P4: Has the agent accounted for all critical observations?
   - P7: Does the content fit within the size bound?

   And: on ANY failure, memory is unchanged.

3. "Why this order?"

   P1 before P3 because: a fabricated chain is cheaper to
   detect than a poison scan. Also, if the chain is invalid,
   the content never reaches the poison scanner — defense
   in depth.

4. "What's the threat model?"

   The agent is the adversary. Not the user, not an external
   attacker — the agent itself. It may hallucinate (unintentional)
   or be manipulated via prompt injection (intentional). Praxis
   treats the agent's conclusions as untrusted until proven.

### What You Should Be Able to Draw

A box diagram:

```text
Observations → [P1: chain valid?] → [P2: consistent?]
  → [P3: not poisoned?] → [P4: complete?] → [P7: bounded?]
  → Write + Certificate
```

With arrows showing: any failure → memory unchanged.

---

## Day 2: The Core Gate — chain_well_formed

**Goal**: Explain exactly how chain_well_formed prevents
hallucination, function by function, and what the F*
ensures clause guarantees.

### Study — Core Gate

Read these files in this order. For each function, write
down in your own words: (a) what it takes, (b) what it
returns, (c) what property it checks.

1. `specs/content/PraxisPredicates.fst` lines 19-23
   (step_premises_valid)

2. `specs/content/PraxisPredicates.fst` lines 54-57
   (identity_valid)

3. `specs/content/PraxisPredicates.fst` lines 79-85
   (rule_obligation_met)

4. `specs/content/PraxisPredicates.fst` lines 89-98
   (chain_well_formed_aux)

5. `specs/content/PraxisPredicates.fst` lines 100-109
   (chain_well_formed)

6. `specs/content/AgentReasoning.fst` lines 9-22
   (inference_sound — the ensures clause)

### F* Syntax You Need to Know (just these)

- `let f (x: t) : r = body` → function definition
- `let rec f ... (decreases x)` → recursive, F* checks
  termination using x getting smaller
- `match x with | pattern -> result` → pattern matching
- `fun x -> body` → anonymous function (lambda)
- `List.Tot.for_all f lst` → true if f is true for every
  element (like Python's `all(f(x) for x in lst)`)
- `List.Tot.existsb f lst` → true if f is true for any
  element (like Python's `any(f(x) for x in lst)`)
- `s :: rest` → list destructuring (head :: tail)
- `Pure bool (requires P) (ensures fun b -> Q)` →
  function returning bool, precondition P, postcondition Q
- `b ==> Q` → logical implication: if b is true, Q holds
- `/\` → logical AND
- `Tot` → total function (always terminates, no side effects)

That's it. You don't need to know Pulse, effects, or monads
for this layer.

### Practice Questions

1. "What does 'grounded in observations' mean precisely?"

   The `known` list starts with the observation contents.
   step_premises_valid checks that every premise in a step
   is in `known`. So every chain of reasoning traces back
   to something the agent actually observed.

2. "Walk me through the canonical example."

   Observation: "The sky is blue"
   Agent claims: Identity rule, conclusion "The economy will crash"

   - known = ["The sky is blue"]
   - step.premises = ["The sky is blue"] — grounding passes
     (the premise IS in known)
   - identity_valid: premises = ["The sky is blue"],
     conclusion = "The economy will crash"
     → "The sky is blue" = "The economy will crash"? No. → false
   - rule_obligation_met dispatches to identity_valid → false
   - chain_well_formed_aux stops. Chain is not well-formed.

3. "Why is string equality the right notion here, not semantic
   similarity?"

   This is a question Coblenz WILL ask. Your answer:
   String equality is decidable, total, and verifiable by Z3.
   Semantic similarity requires an embedding model, is
   approximate, and its correctness is not provable. The
   tradeoff: we lose expressiveness (can't verify "roughly
   the same meaning") but gain a machine-checked guarantee.
   An agent that needs to transform content must use
   Extraction (substring) or Aggregation (bounded recombination)
   rules, which have their own verifiable obligations.

4. "What does the ensures clause on inference_sound actually
   guarantee?"

   ```fstar
   ensures fun b -> b ==>
     chain_well_formed obs_contents chain /\
     chain.final_conclusion = conclusion.me_content
   ```

   "If the function returns true, then (1) the chain is
   well-formed with respect to the observations, AND (2) the
   chain's declared conclusion matches what the agent wants
   to store. The ==> is an implication — when b is false,
   no claim is made. Z3 verified this holds for ALL possible
   inputs at F* compile time."

5. "Could the function just always return false and trivially
   satisfy the ensures clause?"

   YES — the implication would be vacuously true. This is
   where the incorrectness lemmas come in (Day 3).

---

## Day 3: The Proofs — Soundness and Incorrectness

**Goal**: Explain the two-sided proof argument and what Z3
actually does. Be able to answer "is the spec vacuous?"

### Study — Proofs

1. `specs/content/PraxisLemmas.fst` — all of it (174 lines)

   Focus on:
   - L1 (identity_fabrication_rejected) — lines 45-53
   - L7 (contradiction_rejected) — lines 149-173

2. `specs/content/PraxisNormTests.fst` — all of it (217 lines)

   Focus on:
   - Lines 209-216 (the canonical hallucination test)
   - The comment at lines 187-207 (explains the bridge
     between universal and existential)

### Concepts You Need

**Soundness (ensures clauses)**:
"If verification succeeds, properties hold."
∀ inputs. verified(inputs) ⟹ properties(inputs)

**Incorrectness (lemmas)**:
"If the input is fabricated, rejection is guaranteed."
∀ inputs. fabricated(inputs) ⟹ rejected(inputs)

**Together**: The gate is tight. It doesn't accept everything
(would be vacuously sound) and doesn't reject everything
(would be useless).

**assert_norm**: F* evaluates the expression at type-check
time using its normalizer (no Z3 involved). It's a
compile-time unit test. If the expression doesn't reduce
to the expected value, typechecking fails.

**Lemma in F***: A function whose return type is `Lemma`
with requires/ensures. The body must provide evidence that
the ensures holds given the requires. When the body is `()`,
Z3 found the proof automatically. When it's longer (like L7),
F* is guiding Z3 through an inductive argument.

### Practice Questions — Proofs

1. "How do you know the spec isn't vacuously accepting
   everything?"

   The incorrectness lemma identity_fabrication_rejected
   (PraxisLemmas.fst:45-53) proves: for ALL steps claiming
   Identity where conclusion ≠ premise, rule_obligation_met
   returns false. Z3 verified this. The gate provably rejects
   fabricated inputs.

2. "Why does L7 (contradiction_rejected) need a recursive
   proof body when L1 doesn't?"

   L1 is about a single step — Z3 just unfolds identity_valid
   and sees that `p <> conclusion` makes `p = conclusion`
   false. Propositional reasoning.

   L7 involves List.Tot.for_all over a list with a witness
   somewhere inside it. Z3 can't automatically do induction
   over lists — it needs F\* to walk the list recursively
   until the contradicting entry is found, at which point
   the proof is trivial. This is a standard technique:
   F* provides the inductive structure, Z3 closes each case.

3. "What's the relationship between assert_norm and the
   ensures clauses?"

   ensures clauses are UNIVERSAL — they hold for all inputs.
   assert_norm tests are EXISTENTIAL — they confirm a specific
   input evaluates correctly. Together: the ensures clause
   says the property holds everywhere, and assert_norm confirms
   the function actually computes the right answer on concrete
   inputs matching the test suite. It bridges the universal
   proof and the runtime tests.

4. "What does Z3 actually do here?"

   Z3 is an SMT (Satisfiability Modulo Theories) solver.
   F\* translates the ensures clause into a logical formula
   and asks Z3: "Is there any input that makes this false?"
   If Z3 says "unsatisfiable" (no counterexample exists),
   the property is proved. For the incorrectness lemmas,
   F* asks: "Is there any fabricated input where the function
   returns true?" Z3 says no.

---

## Day 4: The Full Picture — What You Prove, What You Don't

**Goal**: Be able to give a 10-minute presentation and handle
Q&A. Know the honest gaps.

### Study — Full Picture

1. `specs/VerifiedWrite.fst` — all 82 lines
   Focus on the ensures clause (lines 32-44)

2. `specs/substrate/AgentState.fst` — 30 lines
   Focus on persist_bounded and the separation logic

3. Skim `src/praxis/server.py` lines 297-337
   (VerifyWrite gRPC handler — the production entry point)

### Pulse/Separation Logic You Need

- `region |-> v` → "this memory region holds value v,
  and I have exclusive ownership"
- `**` → separating conjunction: two resources are
  disjoint (no aliasing)
- `pure (P)` → logical assertion P holds
- `#v: erased string` → ghost variable, exists only in
  the proof, erased at runtime
- `requires R / ensures E` → same as Pure, but for
  stateful (heap-manipulating) code

### The 10-Minute Talk Structure

**Minute 1-2**: The problem.
Hallucination persistence loops. Agent fabricates, stores,
reads back, compounds. Show the 3-turn escalation.

**Minute 3-4**: The solution shape.
Five-check pipeline. Each check is a function with a
machine-checked ensures clause. On failure, memory unchanged.

**Minute 5-7**: The core mechanism.
chain_well_formed. Walk the canonical example.
identity_valid catches fabrication. Show the ensures clause.
Show the incorrectness lemma proving rejection is guaranteed.

**Minute 8-9**: The formal guarantee.
VerifiedWrite.fst ensures clause. On WriteOk: region holds
new content AND all five properties hold (separation logic
ownership + pure logical properties). On failure: region
unchanged. Pulse's separation logic prevents partial writes.

**Minute 10**: Honest gaps and next steps.

- Python runtime is a manual mirror, not extracted from F\*.
  KaRaMeL extraction is the path to closing this.
- Derivation rule is semantically weak — trusts the domain
  rule catalog.
- Poison detection is substring matching, not adversarially
  robust NLP.
- The spec prevents persistence of hallucinations, not
  generation of them. The LLM can still hallucinate —
  it just can't store the hallucination in durable memory.

### Anticipated Hard Questions

**"String equality is too strict / too weak."**
Too strict: yes, it means the Identity rule only applies
to verbatim pass-through. That's intentional — any
transformation must use a different rule with its own
verifiable obligation. Too weak: no, because Derivation
(the escape hatch) still requires grounded premises and a
named domain rule.

**"The Python isn't verified."**
Correct. The F\* proofs cover the specification. The Python
is a manual mirror validated by shared test vectors
(assert_norm in F* and pytest use identical inputs). The
extraction path via KaRaMeL would eliminate this gap. Be
upfront about this.

**"What about multi-step chains where each step is a
Derivation?"**
Each step's premises must be in `known`. The first step's
premises must be observations. So even a chain of derivations
is rooted in real observations. What's NOT guaranteed is that
the derivations are semantically correct — only that they
have non-empty rule IDs and bounded confidence. This is a
deliberate tradeoff: fully verifying semantic correctness
of LLM reasoning is an open problem.

**"How is this different from just validating the output?"**
Output validation is a single check at the end. Praxis
verifies the REASONING CHAIN — every step from observation
to conclusion. This is stronger because it prevents
fabrication at any point in the chain, not just the final
output. It also produces a proof certificate that can be
re-verified later (temporal validity) or by another agent
(witness transport).

**"Could you use a dependent type system instead of
refinement types?"**
F*'s refinement types ARE dependent types — refinements
are a form of dependent type where the type of the return
value depends on the value of the input. The ensures clause
`fun b -> b ==> P` is a dependent return type: the type of
the return varies based on whether b is true or false.
