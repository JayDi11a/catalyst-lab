module ProxyLemmas

open FStar.String
open FStar.List.Tot
open PraxisTypes
open PraxisPredicates
open InferenceProxy

(* === Proxy Incorrectness Lemmas ===

   These lemmas prove that the inference proxy's automatic rule
   classification is TIGHT — it correctly identifies verbatim
   relays, correctly rejects novel content as non-identity, and
   correctly defaults to derivation when no evidence is available.

   Together with the core incorrectness lemmas in PraxisLemmas,
   these ensure the OpenAI-compatible proxy cannot bypass the
   verification gate.

   cf. LBAC/TypeGuard (Zhou et al. 2605.12863):
   The proxy acts as a type-level policy enforcement point —
   classify_rule assigns the weakest rule consistent with the
   available evidence, and these lemmas prove the assignment
   is sound in both directions (correct acceptance AND correct
   rejection). *)


(* --- Auxiliary Lemmas --- *)


(* If a RoleTool message with content = conclusion exists in the
   message list, then conclusion appears in the observation content
   list produced by extract_observations.

   Proof: induction on messages. In the base case (found the matching
   tool message), concatMap produces an observation with obs_content =
   conclusion at the head of the list, so existsb succeeds immediately.
   In the inductive case, the IH provides the result for the tail, and
   the additional observations from the head (if any) are prepended
   without removing the match. *)

let rec tool_msg_in_obs (messages: list chat_message) (conclusion: string)
  : Lemma
    (requires existsb (fun m -> m.cm_role = RoleTool && m.cm_content = conclusion) messages)
    (ensures existsb (fun (s: string) -> s = conclusion)
               (map (fun (o: observation) -> o.obs_content) (concatMap msg_to_obs messages)))
    (decreases messages)
= match messages with
  | [] -> ()
  | m :: rest ->
    if m.cm_role = RoleTool && m.cm_content = conclusion then ()
    else tool_msg_in_obs rest conclusion


(* If no message has content equal to the conclusion, then the
   conclusion does not appear in the observation content list.

   This covers ALL message roles — observations can only contain
   content that originates from some message's cm_content field.
   System and assistant messages produce no observations at all;
   tool and user messages produce observations whose obs_content
   is exactly their cm_content. So if no cm_content matches, no
   obs_content can match either.

   Proof: induction on messages. For each message, either it produces
   no observations (System/Assistant) or it produces one observation
   whose content differs from conclusion (since the precondition
   guarantees cm_content <> conclusion for every message). *)

let rec novel_not_in_obs (messages: list chat_message) (conclusion: string)
  : Lemma
    (requires for_all (fun m -> m.cm_content <> conclusion) messages)
    (ensures existsb (fun (s: string) -> s = conclusion)
               (map (fun (o: observation) -> o.obs_content) (concatMap msg_to_obs messages)) = false)
    (decreases messages)
= match messages with
  | [] -> ()
  | m :: rest ->
    novel_not_in_obs rest conclusion


(* If all messages are System or Assistant, extract_observations
   produces an empty list — no evidence is available.

   Proof: induction on messages. Each message has role System or
   Assistant, so msg_to_obs returns [], and [] @ rest = rest.
   By IH the tail also produces [], so the full result is []. *)

let rec system_assistant_no_obs (messages: list chat_message)
  : Lemma
    (requires for_all (fun m -> m.cm_role = RoleSystem || m.cm_role = RoleAssistant) messages)
    (ensures concatMap msg_to_obs messages == [])
    (decreases messages)
= match messages with
  | [] -> ()
  | m :: rest -> system_assistant_no_obs rest


(* --- Main Lemmas --- *)


(* L_proxy1: Verbatim tool relay is verified as Identity.

   If the proxy receives a tool message whose content is relayed
   verbatim as the conclusion, classify_rule identifies it as
   RuleIdentity. This proves that faithful forwarding of tool
   output is correctly recognized — the proxy does not penalize
   agents that honestly relay evidence.

   Quantified: for ALL message lists containing at least one
   matching tool message, the classification is Identity.
   No false negatives exist for verbatim relay. *)

let verbatim_relay_verified (messages: list chat_message) (conclusion: string)
  : Lemma
    (requires List.Tot.existsb (fun m -> m.cm_role = RoleTool && m.cm_content = conclusion) messages)
    (ensures (let obs = extract_observations messages in
              let obs_c = List.Tot.map (fun (o: observation) -> o.obs_content) obs in
              RuleIdentity? (classify_rule obs_c conclusion)))
= tool_msg_in_obs messages conclusion


(* L_proxy2: Novel content is never classified as Identity.

   If the conclusion does not match ANY message content — tool,
   user, system, or assistant — then classify_rule does not return
   RuleIdentity. This prevents the proxy from falsely attributing
   novel LLM hallucinations to verbatim evidence relay.

   This is the proxy-level defense against hallucination persistence:
   an LLM cannot generate novel content and have it classified as
   a faithful relay of existing evidence.

   Quantified: for ALL message lists where no message content
   matches the conclusion, Identity classification is impossible.
   No false positives exist for novel content. *)

let novel_content_not_identity (messages: list chat_message) (conclusion: string)
  : Lemma
    (requires List.Tot.for_all (fun m -> m.cm_content <> conclusion) messages)
    (ensures (let obs = extract_observations messages in
              let obs_c = List.Tot.map (fun (o: observation) -> o.obs_content) obs in
              RuleIdentity? (classify_rule obs_c conclusion) = false))
= novel_not_in_obs messages conclusion


(* L_proxy3: No evidence forces Derivation classification.

   If all messages are system or assistant messages (no tool or
   user input), there are zero observations. Any non-empty
   conclusion is then classified as RuleDerivation with confidence
   50 — the proxy cannot claim identity, extraction, or aggregation
   without evidence.

   This is the proxy-level analog of L5 (ruleless_derivation_rejected):
   the proxy ensures that evidence-free conclusions are always
   tagged as derivations, making their weak provenance explicit
   to downstream verification.

   Quantified: for ALL message lists containing only system/assistant
   messages, and ALL non-empty conclusions, the classification is
   Derivation with the specific proxy metadata. *)

let no_evidence_means_derivation (messages: list chat_message) (conclusion: string)
  : Lemma
    (requires List.Tot.for_all (fun m -> m.cm_role = RoleSystem || m.cm_role = RoleAssistant) messages /\
             String.length conclusion > 0)
    (ensures (let obs = extract_observations messages in
              let obs_c = List.Tot.map (fun (o: observation) -> o.obs_content) obs in
              List.Tot.length obs_c = 0 /\
              RuleDerivation? (classify_rule obs_c conclusion)))
= system_assistant_no_obs messages
