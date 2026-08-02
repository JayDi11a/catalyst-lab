"""Tests for automatic inference rule classification and observation extraction.

Mirrors the F* InferenceProxy module: classify_rule picks the strongest
applicable rule (Identity > Extraction > Aggregation > Derivation) based
on how the conclusion relates to observed evidence.
"""

from .gateway_client import (
    AggregationEvidence,
    DerivationEvidence,
    ExtractionEvidence,
    InferenceChain,
    Observation,
    RuleKind,
    TrustLevel,
    build_chain_from_proxy,
    classify_rule,
    extract_observations_from_messages,
)


class TestClassifyRule:
    """classify_rule: automatic rule classification from observations."""

    def test_identity_verbatim_match(self):
        obs = ["3 pods running, zero restarts"]
        conclusion = "3 pods running, zero restarts"
        rule = classify_rule(obs, conclusion)
        assert rule.kind == RuleKind.IDENTITY

    def test_identity_picks_first_match(self):
        obs = ["alpha", "beta", "alpha"]
        rule = classify_rule(obs, "alpha")
        assert rule.kind == RuleKind.IDENTITY

    def test_extraction_substring(self):
        obs = ["NAME  READY  STATUS\ngateway  2/2  Running\nagent  3/3  Running"]
        conclusion = "gateway  2/2  Running"
        rule = classify_rule(obs, conclusion)
        assert rule.kind == RuleKind.EXTRACTION
        assert isinstance(rule.evidence, ExtractionEvidence)
        assert rule.evidence.source_premise == obs[0]

    def test_extraction_prefers_identity(self):
        obs = ["hello world", "hello"]
        conclusion = "hello"
        rule = classify_rule(obs, conclusion)
        assert rule.kind == RuleKind.IDENTITY

    def test_aggregation_shorter_than_combined(self):
        obs = ["pod A is running", "pod B is running", "pod C is running"]
        conclusion = "3 pods running"
        rule = classify_rule(obs, conclusion)
        assert rule.kind == RuleKind.AGGREGATION
        assert isinstance(rule.evidence, AggregationEvidence)
        assert rule.evidence.source_premises == obs

    def test_derivation_longer_than_combined(self):
        obs = ["ok"]
        conclusion = "The cluster is healthy and all services are operational"
        rule = classify_rule(obs, conclusion)
        assert rule.kind == RuleKind.DERIVATION
        assert isinstance(rule.evidence, DerivationEvidence)
        assert rule.evidence.confidence == 50
        assert rule.evidence.domain_rule_id == "llm-inference"

    def test_derivation_no_observations(self):
        rule = classify_rule([], "some conclusion")
        assert rule.kind == RuleKind.DERIVATION

    def test_hallucination_not_identity(self):
        obs = ["3 pods running, zero restarts"]
        conclusion = "The cluster is overloaded and will crash"
        rule = classify_rule(obs, conclusion)
        assert rule.kind != RuleKind.IDENTITY

    def test_empty_conclusion_is_identity_if_empty_obs(self):
        rule = classify_rule([""], "")
        assert rule.kind == RuleKind.IDENTITY


class TestExtractObservations:
    """extract_observations_from_messages: OpenAI message array parsing."""

    def test_tool_message(self):
        messages = [{"role": "tool", "tool_call_id": "call_1", "content": "3 pods running"}]
        obs = extract_observations_from_messages(messages)
        assert len(obs) == 1
        assert obs[0].trust == TrustLevel.TOOL_OUTPUT
        assert obs[0].content == "3 pods running"
        assert obs[0].tool_call_id == "call_1"
        assert obs[0].source == "tool:call_1"

    def test_user_message(self):
        messages = [{"role": "user", "content": "What is the pod status?"}]
        obs = extract_observations_from_messages(messages)
        assert len(obs) == 1
        assert obs[0].trust == TrustLevel.EXTERNAL_INPUT
        assert obs[0].source == "user"

    def test_system_and_assistant_filtered(self):
        messages = [
            {"role": "system", "content": "You are Hermes"},
            {"role": "assistant", "content": "Let me check"},
            {"role": "tool", "tool_call_id": "c1", "content": "data"},
        ]
        obs = extract_observations_from_messages(messages)
        assert len(obs) == 1
        assert obs[0].content == "data"

    def test_empty_messages(self):
        assert extract_observations_from_messages([]) == []

    def test_null_content_handled(self):
        messages = [{"role": "assistant", "content": None}]
        obs = extract_observations_from_messages(messages)
        assert len(obs) == 0

    def test_tool_without_call_id(self):
        messages = [{"role": "tool", "content": "result"}]
        obs = extract_observations_from_messages(messages)
        assert obs[0].source == "tool:unknown"

    def test_multi_turn_conversation(self):
        messages = [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Check pods"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "c1", "function": {"name": "kubectl"}}],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "2 pods running"},
            {"role": "assistant", "content": "Let me also check services"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "c2", "function": {"name": "kubectl"}}],
            },
            {"role": "tool", "tool_call_id": "c2", "content": "3 services active"},
        ]
        obs = extract_observations_from_messages(messages)
        assert len(obs) == 3
        assert obs[0].source == "user"
        assert obs[1].source == "tool:c1"
        assert obs[2].source == "tool:c2"


class TestBuildChainFromProxy:
    """build_chain_from_proxy: construct verified chain from observations."""

    def test_identity_chain(self):
        obs = [Observation(source="tool:c1", content="data", trust=TrustLevel.TOOL_OUTPUT)]
        chain = build_chain_from_proxy(obs, "data")
        assert isinstance(chain, InferenceChain)
        assert len(chain.steps) == 1
        assert chain.steps[0].rule.kind == RuleKind.IDENTITY
        assert chain.final_conclusion == "data"
        assert chain.steps[0].premises == ["data"]

    def test_derivation_chain(self):
        obs = [Observation(source="tool:c1", content="ok", trust=TrustLevel.TOOL_OUTPUT)]
        chain = build_chain_from_proxy(obs, "Everything is healthy and running smoothly")
        assert chain.steps[0].rule.kind == RuleKind.DERIVATION

    def test_empty_observations(self):
        chain = build_chain_from_proxy([], "some conclusion")
        assert chain.steps[0].rule.kind == RuleKind.DERIVATION
        assert chain.steps[0].premises == []
