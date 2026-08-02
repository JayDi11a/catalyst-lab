module DemoChallenge

open FStar.List.Tot
open FStar.String
open PraxisTypes
open PraxisPredicates

(* ═══════════════════════════════════════════════════════════════
   Demo Challenge — Professor Coblenz, July 25, 2026

   Three lemmas with admit() holes. The AI agent (Claude Code +
   proof-copilot) will fill them in using fstar-mcp for
   interactive typechecking.

   Each lemma proves a SAFETY property about the Praxis
   verification pipeline — these are incorrectness lemmas
   in the style of Gardner (OPLSS 2026): they show that
   specific attack patterns are NECESSARILY rejected.

   Difficulty: progressive.
   ═══════════════════════════════════════════════════════════════ *)


(* ─── L_demo1: Identity requires a premise ───

   The identity rule means "conclusion = observation."
   It requires EXACTLY one premise. If an agent claims
   identity with zero premises, it has no observation to
   ground the conclusion — pure fabrication.

   Prove: identity with empty premises is always rejected. *)

let identity_no_premises_rejected (step: inference_step)
  : Lemma
    (requires RuleIdentity? step.rule /\ step.premises == [])
    (ensures rule_obligation_met step = false)
= ()


(* ─── L_demo2: Identity is exact ───

   The REVERSE direction: if identity_valid SUCCEEDS, then
   the conclusion is EXACTLY the sole premise. No transformation,
   no synthesis, no summarization — pure relay.

   This is the core guarantee preventing hallucination
   persistence: what enters memory is literally what was
   observed.

   Prove: identity_valid = true implies conclusion equals
   the single premise. *)

let identity_is_exact (step: inference_step)
  : Lemma
    (requires
      RuleIdentity? step.rule /\
      identity_valid step = true)
    (ensures
      (match step.premises with
       | [single] -> step.step_conclusion = single
       | _ -> False))
= ()


(* ─── L_demo3: Confidence is bounded ───

   Even at the weakest verification level (RuleDerivation —
   domain-specific abductive reasoning), the system enforces
   bounds. An agent cannot inflate its confidence score
   beyond [0, 100] to mask uncertainty.

   Note: this lemma gives a valid rule_id (length > 0),
   so the ONLY reason for rejection is the confidence bound.
   The system is not rejecting on a technicality — it is
   enforcing the semantic invariant.

   Prove: derivation with confidence > 100 is rejected,
   even when all other evidence is valid. *)

let derivation_confidence_bounded (step: inference_step)
  : Lemma
    (requires
      (match step.rule with
       | RuleDerivation ev ->
           String.length ev.de_domain_rule_id > 0 /\
           ev.de_confidence > 100
       | _ -> False))
    (ensures rule_obligation_met step = false)
= ()
