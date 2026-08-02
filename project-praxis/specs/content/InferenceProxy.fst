module InferenceProxy

open FStar.List.Tot
open FStar.String
open PraxisTypes
open PraxisPredicates

(* --- OpenAI Chat Completion API Types ---

   Models the message structure of the OpenAI chat completion API
   as used by the inference proxy. Only the role and content fields
   are relevant for provenance tracking — other fields (model,
   temperature, etc.) do not affect the inference chain. *)

type message_role =
  | RoleTool
  | RoleUser
  | RoleSystem
  | RoleAssistant

noeq
type chat_message = {
  cm_role: message_role;
  cm_content: string;
}

(* --- Message to Observation Conversion ---

   Each message role maps to a specific trust level:
   - RoleTool    -> ToolOutput      (tool produced this content)
   - RoleUser    -> ExternalInput   (human provided this content)
   - RoleSystem  -> (no observation — instructions, not evidence)
   - RoleAssistant -> (no observation — prior completions, not evidence) *)

let msg_to_obs (m: chat_message) : list observation =
  match m.cm_role with
  | RoleTool -> [{ obs_source = "tool";
                   obs_content = m.cm_content;
                   obs_trust = ToolOutput;
                   obs_tool_call_id = None }]
  | RoleUser -> [{ obs_source = "user";
                   obs_content = m.cm_content;
                   obs_trust = ExternalInput;
                   obs_tool_call_id = None }]
  | _ -> []

(* --- Observation Extraction ---

   Filters chat messages to extract only those that constitute
   evidence (tool outputs and user inputs). System and assistant
   messages are not evidence — they are instructions or prior
   completions that cannot ground new claims. *)

let extract_observations (messages: list chat_message) : list observation =
  List.Tot.concatMap msg_to_obs messages

(* --- Automatic Inference Rule Classification ---

   Given a set of observation contents and a conclusion (the LLM's
   response), classifies the inference rule that best describes how
   the conclusion relates to the available evidence:

   1. Identity:    conclusion matches an observation verbatim
                   (faithful relay of tool/user content)
   2. Extraction:  conclusion is a substring of some observation
                   (selected portion of evidence)
   3. Aggregation: conclusion length <= total observation length
                   (synthesis from multiple observations)
   4. Derivation:  fallback — novel content exceeding the available
                   evidence, classified with confidence 50

   The classification is conservative: it assigns the STRONGEST
   rule whose structural precondition is met. Identity is strongest
   (exact match), derivation is weakest (no structural evidence). *)

let classify_rule (obs_contents: list string) (conclusion: string) : inference_rule =
  if List.Tot.existsb (fun o -> o = conclusion) obs_contents then
    RuleIdentity
  else
    match List.Tot.find (fun o -> contains_substring o conclusion) obs_contents with
    | Some matching ->
      RuleExtraction ({ ext_source_premise = matching })
    | None ->
      if String.length conclusion <= total_string_length obs_contents then
        RuleAggregation ({ agg_source_premises = obs_contents })
      else
        RuleDerivation ({ de_domain_rule_id = "llm-inference";
                          de_rule_desc = "proxy-classified";
                          de_confidence = 50 })
