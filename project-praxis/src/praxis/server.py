"""Praxis Verification Gateway — gRPC server.

Wraps the five verification surfaces (P1-P10) as a gRPC service.
The proto stubs are generated at container build time; the try/except
import allows running tests and linters before code-gen.

Health endpoints on :8080 let Kubernetes probes work without gRPC
health-checking support in the load balancer.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from concurrent import futures
from http.server import BaseHTTPRequestHandler, HTTPServer

import grpc

# Proto stubs are generated at build time.  Fall back to top-level
# import so the module is still importable during local development.
try:
    from . import praxis_pb2, praxis_pb2_grpc
except ImportError:
    import praxis_pb2
    import praxis_pb2_grpc  # type: ignore[no-redef]

from .gateway_client import (
    AggregationEvidence,
    DerivationEvidence,
    DomainSpec,
    ExtractionEvidence,
    InferenceChain,
    InferenceRule,
    InferenceStep,
    MemoryEntry,
    MemoryIntent,
    MemoryState,
    Observation,
    PoisonPatterns,
    PraxisGatewayClient,
    ProofCertificate,
    ProofWitness,
    RuleKind,
    SkillCode,
    SkillSpec,
    TemporalCertificate,
    ToolCallRecord,
    ToolDeclaration,
    ToolEvidence,
    TrustLevel,
    call_within_scope,
    certificate_reverify,
    cross_agent_verify,
    side_effects_contained,
    skill_interface_valid,
    skill_safe_to_persist,
    skill_tools_within_scope,
    tool_invocation_safe,
    witness_has_minimum_properties,
    witness_well_formed,
)
from .gateway_client import (
    ToolResult as GatewayToolResult,
)

logger = logging.getLogger("praxis.server")

# ---------------------------------------------------------------------------
# Protobuf  <-->  Python dataclass converters
# ---------------------------------------------------------------------------

_TRUST_MAP: dict[int, TrustLevel] = {
    praxis_pb2.DIRECT_OBSERVATION: TrustLevel.DIRECT_OBSERVATION,
    praxis_pb2.TOOL_OUTPUT: TrustLevel.TOOL_OUTPUT,
    praxis_pb2.EXTERNAL_INPUT: TrustLevel.EXTERNAL_INPUT,
    praxis_pb2.AGENT_GENERATED: TrustLevel.AGENT_GENERATED,
    praxis_pb2.UNVERIFIED: TrustLevel.UNVERIFIED,
}

_TRUST_REVERSE: dict[TrustLevel, int] = {v: k for k, v in _TRUST_MAP.items()}


def _proto_to_rule(rule_proto) -> InferenceRule:
    """Convert a protobuf InferenceRule oneof into a Python InferenceRule."""
    which = rule_proto.WhichOneof("rule")
    if which == "identity":
        return InferenceRule(kind=RuleKind.IDENTITY)
    if which == "extraction":
        ev = rule_proto.extraction
        return InferenceRule(
            kind=RuleKind.EXTRACTION,
            evidence=ExtractionEvidence(source_premise=ev.source_premise),
        )
    if which == "aggregation":
        ev = rule_proto.aggregation
        return InferenceRule(
            kind=RuleKind.AGGREGATION,
            evidence=AggregationEvidence(source_premises=list(ev.source_premises)),
        )
    if which == "tool_result":
        ev = rule_proto.tool_result
        return InferenceRule(
            kind=RuleKind.TOOL_RESULT,
            evidence=ToolEvidence(
                tool_name=ev.tool_name,
                call_id=ev.call_id,
                tool_trusted=ev.tool_trusted,
            ),
        )
    if which == "derivation":
        ev = rule_proto.derivation
        return InferenceRule(
            kind=RuleKind.DERIVATION,
            evidence=DerivationEvidence(
                domain_rule_id=ev.domain_rule_id,
                rule_desc=ev.rule_description,
                confidence=ev.confidence,
            ),
        )
    # Unset oneof — treat as identity (defensive)
    return InferenceRule(kind=RuleKind.IDENTITY)


def _proto_to_observation(obs) -> Observation:
    trust = _TRUST_MAP.get(obs.trust, TrustLevel.UNVERIFIED)
    tool_call_id = obs.tool_call_id if obs.HasField("tool_call_id") else None
    return Observation(
        source=obs.source,
        content=obs.content,
        trust=trust,
        tool_call_id=tool_call_id,
    )


def _proto_to_step(step) -> InferenceStep:
    return InferenceStep(
        premises=list(step.premises),
        rule=_proto_to_rule(step.rule),
        conclusion=step.conclusion,
    )


def _proto_to_chain(chain) -> InferenceChain:
    return InferenceChain(
        steps=[_proto_to_step(s) for s in chain.steps],
        final_conclusion=chain.final_conclusion,
    )


def _proto_to_memory_entry(entry) -> MemoryEntry:
    return MemoryEntry(
        key=entry.key,
        content=entry.content,
        source_trusted=entry.source_trusted,
        trace_id=entry.trace_id,
    )


def _proto_to_poison_patterns(pp) -> PoisonPatterns:
    return PoisonPatterns(
        instruction_overrides=list(pp.instruction_overrides),
        role_escalations=list(pp.role_escalations),
        exfiltration_markers=list(pp.exfiltration_markers),
    )


def _proto_to_domain_spec(ds) -> DomainSpec:
    return DomainSpec(
        critical_patterns=list(ds.critical_patterns),
        required_keys=list(ds.required_keys),
    )


def _proto_to_skill_spec(spec) -> SkillSpec:
    return SkillSpec(
        name=spec.name,
        inputs=list(spec.inputs),
        output_type=spec.output_type,
        max_body_size=spec.max_body_size,
        allowed_tools=list(spec.allowed_tools),
    )


def _proto_to_skill_code(code) -> SkillCode:
    return SkillCode(
        name=code.name,
        body=code.body,
        declared_inputs=list(code.declared_inputs),
        declared_output=code.declared_output,
        tool_calls=list(code.tool_calls),
    )


def _proto_to_tool_decl(decl) -> ToolDeclaration:
    return ToolDeclaration(
        name=decl.name,
        allowed_args=list(decl.allowed_args),
        output_type=decl.output_type,
        side_effects=list(decl.declared_side_effects),
    )


def _proto_to_tool_call(call) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=call.tool_name,
        arguments=list(call.arguments),
    )


def _proto_to_tool_result(result) -> GatewayToolResult:
    return GatewayToolResult(
        output=result.output,
        observed_side_effects=list(result.observed_side_effects),
    )


def _proto_to_proof_witness(w) -> ProofWitness:
    return ProofWitness(
        source_agent=w.source_agent,
        content_hash=w.content_hash,
        rule_used=_proto_to_rule(w.rule_used),
        properties=list(w.properties),
        obs_count=w.observation_count,
        source_trusted=w.source_trusted,
    )


def _rule_to_proto(rule: InferenceRule):
    """Convert a Python InferenceRule to a protobuf InferenceRule."""
    proto = praxis_pb2.InferenceRule()
    if rule.kind == RuleKind.IDENTITY:
        proto.identity.CopyFrom(praxis_pb2.IdentityRule())
    elif rule.kind == RuleKind.EXTRACTION and rule.evidence:
        proto.extraction.CopyFrom(
            praxis_pb2.ExtractionRule(source_premise=rule.evidence.source_premise)
        )
    elif rule.kind == RuleKind.AGGREGATION and rule.evidence:
        proto.aggregation.CopyFrom(
            praxis_pb2.AggregationRule(source_premises=rule.evidence.source_premises)
        )
    elif rule.kind == RuleKind.TOOL_RESULT and rule.evidence:
        proto.tool_result.CopyFrom(
            praxis_pb2.ToolResultRule(
                tool_name=rule.evidence.tool_name,
                call_id=rule.evidence.call_id,
                tool_trusted=rule.evidence.tool_trusted,
            )
        )
    elif rule.kind == RuleKind.DERIVATION and rule.evidence:
        proto.derivation.CopyFrom(
            praxis_pb2.DerivationRule(
                domain_rule_id=rule.evidence.domain_rule_id,
                rule_description=rule.evidence.rule_desc,
                confidence=rule.evidence.confidence,
            )
        )
    return proto


def _cert_to_proto(cert: ProofCertificate):
    """Convert a Python ProofCertificate to a protobuf ProofCertificate."""
    return praxis_pb2.ProofCertificate(
        trace_id=cert.trace_id,
        content_hash=cert.content_hash,
        rule_used=_rule_to_proto(cert.rule_used),
        properties_satisfied=cert.properties_satisfied,
        timestamp=cert.timestamp,
        observation_count=cert.obs_count,
    )


# ---------------------------------------------------------------------------
# gRPC Servicer
# ---------------------------------------------------------------------------


class PraxisGatewayServicer(praxis_pb2_grpc.PraxisGatewayServicer):
    """Implements all six verification RPCs plus health."""

    def __init__(self):
        self._client = PraxisGatewayClient()
        logger.info("PraxisGatewayServicer initialized")

    # -- Composed pipeline (Surface 1-5) --

    def VerifyWrite(self, request, context):
        logger.debug("VerifyWrite trace_id=%s", request.trace_id)

        observations = [_proto_to_observation(o) for o in request.observations]
        chain = _proto_to_chain(request.chain)
        conclusion = _proto_to_memory_entry(request.entry)
        existing = MemoryState(facts=[_proto_to_memory_entry(m) for m in request.existing_memory])
        poison_patterns = _proto_to_poison_patterns(request.poison_patterns)
        domain_spec = _proto_to_domain_spec(request.domain_spec)

        intent = MemoryIntent(
            agent_id=request.trace_id,
            observations=observations,
            chain=chain,
            conclusion=conclusion,
            existing=existing,
            bound=request.tier1_bound,
            poison_patterns=poison_patterns,
            domain_spec=domain_spec,
        )

        result = self._client.verify_write(intent)

        resp = praxis_pb2.VerifyWriteResponse(
            properties_satisfied=result.properties_satisfied,
        )

        if result.result.value == "WriteOk":
            resp.status = praxis_pb2.VerifyWriteResponse.WRITE_OK
            if result.certificate:
                resp.certificate.CopyFrom(_cert_to_proto(result.certificate))
        else:
            resp.status = praxis_pb2.VerifyWriteResponse.WRITE_REJECTED
            resp.violations.append(result.result.value)

        return resp

    # -- Surface 1: Inference chain soundness --

    def VerifyInference(self, request, context):
        logger.debug("VerifyInference trace_id=%s", request.trace_id)

        chain = _proto_to_chain(request.chain)
        observations = [_proto_to_observation(o) for o in request.observations]
        obs_contents = [o.content for o in observations]

        from .gateway_client import _chain_well_formed

        valid = _chain_well_formed(obs_contents, chain)

        properties = []
        violations = []
        if valid:
            properties.append("P1:inference_sound")
        else:
            violations.append("P1:chain_not_well_formed")

        return praxis_pb2.VerifyInferenceResponse(
            valid=valid,
            properties_satisfied=properties,
            violations=violations,
        )

    # -- Surface 2: Skill verification --

    def VerifySkill(self, request, context):
        logger.debug("VerifySkill trace_id=%s", request.trace_id)

        spec = _proto_to_skill_spec(request.spec)
        code = _proto_to_skill_code(request.code)
        pp = _proto_to_poison_patterns(request.poison_patterns)

        iface_valid = skill_interface_valid(spec, code)
        tools_ok = skill_tools_within_scope(spec, code)
        from .gateway_client import _content_safe

        content_ok = _content_safe(code.body, pp)
        safe = skill_safe_to_persist(spec, code, pp)

        violations = []
        if not iface_valid:
            violations.append("interface_mismatch")
        if not tools_ok:
            violations.append("unauthorized_tool_call")
        if not content_ok:
            violations.append("poisoned_content")

        return praxis_pb2.VerifySkillResponse(
            safe_to_persist=safe,
            interface_valid=iface_valid,
            tools_within_scope=tools_ok,
            content_safe=content_ok,
            violations=violations,
        )

    # -- Surface 3: Tool invocation trust --

    def VerifyToolInvocation(self, request, context):
        logger.debug("VerifyToolInvocation trace_id=%s", request.trace_id)

        decl = _proto_to_tool_decl(request.declaration)
        call = _proto_to_tool_call(request.call)
        result = _proto_to_tool_result(request.result)

        scope_ok = call_within_scope(decl, call)
        effects_ok = side_effects_contained(decl, call, result)
        safe = tool_invocation_safe(decl, call, result)

        violations = []
        if not scope_ok:
            violations.append("P9:call_outside_scope")
        if not effects_ok:
            violations.append("P10:undeclared_side_effects")

        return praxis_pb2.VerifyToolInvocationResponse(
            safe=safe,
            call_within_scope=scope_ok,
            side_effects_contained=effects_ok,
            violations=violations,
        )

    # -- Surface 4: Temporal validity --

    def VerifyTemporal(self, request, context):
        logger.debug("VerifyTemporal trace_id=%s", request.trace_id)

        cert_proto = request.certificate
        cert = ProofCertificate(
            trace_id=cert_proto.trace_id,
            content_hash=cert_proto.content_hash,
            rule_used=_proto_to_rule(cert_proto.rule_used),
            properties_satisfied=list(cert_proto.properties_satisfied),
            timestamp=cert_proto.timestamp,
            obs_count=cert_proto.observation_count,
        )

        tc = TemporalCertificate(
            cert=cert,
            valid_from=request.valid_from,
            valid_until=request.valid_until,
        )

        valid = certificate_reverify(tc, request.stored_content_hash, request.current_time)

        from .gateway_client import certificate_content_matches, certificate_valid_at

        in_window = certificate_valid_at(tc, request.current_time)
        content_ok = certificate_content_matches(cert, request.stored_content_hash)

        violations = []
        if not in_window:
            violations.append("certificate_expired")
        if not content_ok:
            violations.append("content_hash_mismatch")

        return praxis_pb2.VerifyTemporalResponse(
            valid=valid,
            within_time_window=in_window,
            content_matches=content_ok,
            violations=violations,
        )

    # -- Surface 5: Proof witness transport --

    def VerifyWitness(self, request, context):
        logger.debug("VerifyWitness trace_id=%s", request.trace_id)

        witness = _proto_to_proof_witness(request.witness)

        wf = witness_well_formed(witness)
        content_ok = cross_agent_verify(witness, request.stored_content_hash)
        props_ok = witness_has_minimum_properties(witness, list(request.required_properties))
        valid = wf and content_ok and props_ok

        violations = []
        if not wf:
            violations.append("witness_malformed")
        if not content_ok:
            violations.append("content_hash_mismatch")
        if not props_ok:
            violations.append("missing_required_properties")

        return praxis_pb2.VerifyWitnessResponse(
            valid=valid,
            well_formed=wf,
            content_matches=content_ok if wf else False,
            has_required_properties=props_ok,
            violations=violations,
        )

    # -- Health --

    def Health(self, request, context):
        # Report tool versions; F*/Z3 are not installed in the
        # Python-mirror image, so we report "python-mirror".
        return praxis_pb2.HealthResponse(
            healthy=True,
            fstar_version="python-mirror",
            z3_version="python-mirror",
            specs_loaded=0,
        )


# ---------------------------------------------------------------------------
# HTTP health server (for K8s probes that don't speak gRPC)
# ---------------------------------------------------------------------------

_healthy = threading.Event()


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for /healthz and /readyz."""

    def do_GET(self):
        if self.path in ("/healthz", "/readyz"):
            if _healthy.is_set():
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"not ready")
        else:
            self.send_response(404)
            self.end_headers()

    # Suppress per-request log lines — they clutter the pod logs.
    def log_message(self, format, *args):
        return


def _run_health_server(port: int = 8080) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("HTTP health server listening on :%d", port)
    return server


# ---------------------------------------------------------------------------
# OTel bootstrap (optional)
# ---------------------------------------------------------------------------


def _setup_otel():
    """Configure OpenTelemetry gRPC interceptor if the env var is set."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set — tracing disabled")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "praxis-gateway"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OTel tracing enabled — exporting to %s", endpoint)
        return provider
    except ImportError:
        logger.warning(
            "OTel packages not installed — tracing disabled "
            "(install opentelemetry-sdk and opentelemetry-exporter-otlp-proto-grpc)"
        )
        return None


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

_GRPC_PORT = 50051
_HEALTH_PORT = 8080


def serve():
    """Start the Praxis gRPC gateway and HTTP health server."""

    log_level = os.environ.get("PRAXIS_LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    logger.info("Starting Praxis Verification Gateway")

    _setup_otel()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    praxis_pb2_grpc.add_PraxisGatewayServicer_to_server(PraxisGatewayServicer(), server)
    server.add_insecure_port(f"[::]:{_GRPC_PORT}")
    server.start()
    logger.info("gRPC server listening on :%d", _GRPC_PORT)

    health_server = _run_health_server(_HEALTH_PORT)
    _healthy.set()

    # Graceful shutdown on SIGTERM (sent by Kubernetes)
    stop_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Received signal %d — shutting down", signum)
        _healthy.clear()
        server.stop(grace=5)
        health_server.shutdown()
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Praxis Gateway ready")
    stop_event.wait()
    logger.info("Praxis Gateway stopped")


if __name__ == "__main__":
    serve()
