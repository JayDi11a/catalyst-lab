module AgentReasoning

open FStar.List.Tot
open PraxisTypes
open PraxisPredicates
open PoisonDetection
open CompletenessCheck

let inference_sound
  (observations: list observation)
  (chain: inference_chain)
  (conclusion: memory_entry)
  : Pure bool
    (requires True)
    (ensures fun b -> b ==>
      chain_well_formed (List.Tot.map (fun (o: observation) -> o.obs_content) observations) chain /\
      chain.final_conclusion = conclusion.me_content)
=
  let obs_contents = List.Tot.map (fun (o: observation) -> o.obs_content) observations in
  let wf = chain_well_formed obs_contents chain in
  let conclusion_matches = chain.final_conclusion = conclusion.me_content in
  wf && conclusion_matches

let consistent_with
  (new_fact: memory_entry)
  (existing: memory_state)
  : Pure bool
    (requires True)
    (ensures fun b -> b ==> no_contradiction new_fact existing)
=
  no_contradiction new_fact existing

let not_poisoned
  (entry: memory_entry)
  (pp: poison_patterns)
  : Pure bool
    (requires True)
    (ensures fun b -> b ==>
      content_safe entry.me_content pp /\
      entry.me_source_trusted)
=
  content_safe entry.me_content pp && entry.me_source_trusted

let memory_complete
  (observations: list observation)
  (memory: memory_state)
  (spec: domain_spec)
  : Pure bool
    (requires True)
    (ensures fun b -> b ==> memory_is_complete observations memory spec)
=
  memory_is_complete observations memory spec
