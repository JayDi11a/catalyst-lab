module PraxisNormTests

open PraxisTypes
open PraxisPredicates

(* === F* Normalization Tests ===

   These evaluate the SAME test vectors used in the Python test suite
   inside the F* type checker at verification time.

   assert_norm: normalizes a pure expression at typechecking time,
   then asserts the result. If the function evaluates to the expected
   value, the assertion holds WITHOUT Z3 — pure computation in the
   type checker.

   This bridges the gap between:
   - F* universal proofs: "for ALL inputs satisfying preconditions,
     properties hold" (proved via Z3)
   - Python existential tests: "for THIS specific input, the function
     returns THIS specific output" (checked via pytest)

   By evaluating F* specs on concrete inputs at type-check time, we
   prove the specification COMPUTES correctly — not just that it
   type-checks.

   cf. Dafny-as-intermediate-language (Li et al. 2501.06283):
   F* is our verification-aware intermediate language. These tests
   show F* evaluating the same concrete scenarios the runtime handles,
   confirming spec and implementation agree on specific inputs. *)


(* ──────────────────────────────────────────────────────────────────
   Identity Rule
   Python: test_p1_semantic.py::TestIdentityRule
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  identity_valid ({
    premises = ["GPU utilization at 87%"];
    rule = RuleIdentity;
    step_conclusion = "GPU utilization at 87%"
  }) = true)

let _ = assert_norm (
  identity_valid ({
    premises = ["GPU at 87%"];
    rule = RuleIdentity;
    step_conclusion = "GPU at 90%"
  }) = false)

let _ = assert_norm (
  identity_valid ({
    premises = ["fact A"; "fact B"];
    rule = RuleIdentity;
    step_conclusion = "fact A"
  }) = false)


(* ──────────────────────────────────────────────────────────────────
   Extraction Rule
   Python: test_p1_semantic.py::TestExtractionRule
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  extraction_valid
    ({ premises = ["GPU peaked at 87% during benchmark"];
       rule = RuleExtraction ({ ext_source_premise = "GPU peaked at 87% during benchmark" });
       step_conclusion = "87%" })
    ({ ext_source_premise = "GPU peaked at 87% during benchmark" })
  = true)

let _ = assert_norm (
  extraction_valid
    ({ premises = ["GPU peaked at 87%"];
       rule = RuleExtraction ({ ext_source_premise = "GPU peaked at 87%" });
       step_conclusion = "99%" })
    ({ ext_source_premise = "GPU peaked at 87%" })
  = false)


(* ──────────────────────────────────────────────────────────────────
   Aggregation Rule
   Python: test_p1_semantic.py::TestAggregationRule
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  aggregation_valid
    ({ premises = ["GPU at 87%"; "latency 45ms"];
       rule = RuleAggregation ({ agg_source_premises = ["GPU at 87%"; "latency 45ms"] });
       step_conclusion = "GPU 87% lat 45ms" })
    ({ agg_source_premises = ["GPU at 87%"; "latency 45ms"] })
  = true)

let _ = assert_norm (
  aggregation_valid
    ({ premises = ["short"];
       rule = RuleAggregation ({ agg_source_premises = ["short"] });
       step_conclusion = "this exceeds the combined premise length" })
    ({ agg_source_premises = ["short"] })
  = false)


(* ──────────────────────────────────────────────────────────────────
   Tool Result Rule
   Python: test_p1_semantic.py::TestToolResultRule
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  tool_result_valid
    ({ premises = ["kubectl: 3 pods running"];
       rule = RuleToolResult ({ te_tool_name = "kubectl"; te_call_id = "c1"; te_tool_trusted = true });
       step_conclusion = "kubectl: 3 pods running" })
    ({ te_tool_name = "kubectl"; te_call_id = "c1"; te_tool_trusted = true })
  = true)

let _ = assert_norm (
  tool_result_valid
    ({ premises = ["output"];
       rule = RuleToolResult ({ te_tool_name = "unknown"; te_call_id = "c2"; te_tool_trusted = false });
       step_conclusion = "output" })
    ({ te_tool_name = "unknown"; te_call_id = "c2"; te_tool_trusted = false })
  = false)


(* ──────────────────────────────────────────────────────────────────
   Derivation Rule
   Python: test_p1_semantic.py::TestDerivationRule
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  derivation_valid
    ({ premises = ["latency > 200ms three times"];
       rule = RuleDerivation ({ de_domain_rule_id = "sli-breach"; de_rule_desc = "3 SLI violations"; de_confidence = 90 });
       step_conclusion = "service degraded" })
    ({ de_domain_rule_id = "sli-breach"; de_rule_desc = "3 SLI violations"; de_confidence = 90 })
  = true)

let _ = assert_norm (
  derivation_valid
    ({ premises = ["data"];
       rule = RuleDerivation ({ de_domain_rule_id = ""; de_rule_desc = "no rule"; de_confidence = 50 });
       step_conclusion = "conclusion" })
    ({ de_domain_rule_id = ""; de_rule_desc = "no rule"; de_confidence = 50 })
  = false)


(* ──────────────────────────────────────────────────────────────────
   Rule Obligation Met (dispatcher)
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  rule_obligation_met ({
    premises = ["GPU utilization at 87%"];
    rule = RuleIdentity;
    step_conclusion = "GPU utilization at 87%"
  }) = true)

let _ = assert_norm (
  rule_obligation_met ({
    premises = ["GPU at 87%"];
    rule = RuleIdentity;
    step_conclusion = "FABRICATED"
  }) = false)


(* ──────────────────────────────────────────────────────────────────
   Chain Well-Formedness
   Python: test_p1_semantic.py::TestChainOrdering
   ────────────────────────────────────────────────────────────────── *)

let _ = assert_norm (
  chain_well_formed
    ["GPU utilization at 87%"]
    ({ steps = [{ premises = ["GPU utilization at 87%"];
                  rule = RuleIdentity;
                  step_conclusion = "GPU utilization at 87%" }];
       final_conclusion = "GPU utilization at 87%" })
  = true)

let _ = assert_norm (
  chain_well_formed
    ["anything"]
    ({ steps = []; final_conclusion = "anything" })
  = false)


(* ══════════════════════════════════════════════════════════════════
   THE CANONICAL TEST: Hallucination Persistence Loop

   An agent observes "The sky is blue" and concludes
   "The economy will crash." Using an identity rule, which
   requires conclusion = premise.

   Phase 1 (structural only) accepted this — the chain shape
   was valid. Phase 2 (semantic) rejects it — identity requires
   exact match.

   F* evaluates this at type-check time, proving the spec
   rejects this fabrication on this SPECIFIC input — matching
   the Python test:
     test_p1_semantic.py::TestHallucinationPersistenceLoop
       ::test_sky_blue_economy_crash_rejected

   This is the bridge between universal proof and existential
   test: F* proves the property for ALL inputs (via Z3), AND
   evaluates the SAME concrete input Python tests (via assert_norm).
   ══════════════════════════════════════════════════════════════════ *)

let _ = assert_norm (
  chain_well_formed
    ["The sky is blue"]
    ({ steps = [{ premises = ["The sky is blue"];
                  rule = RuleIdentity;
                  step_conclusion = "The economy will crash" }];
       final_conclusion = "The economy will crash" })
  = false)
