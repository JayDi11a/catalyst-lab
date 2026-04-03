#!/usr/bin/env python3
"""
Bulk Document Upload to LLaMA Stack
Uploads text files to LLaMA Stack which handles chunking, embedding, and storage.
"""

import os
import sys
import time
from pathlib import Path
import requests
import yaml


# Sample technical documents to add more data
SAMPLE_DOCUMENTS = {
    "ai_transformers.txt": """
# Transformer Architecture in Modern AI

The Transformer architecture, introduced in "Attention is All You Need" (2017), revolutionized
natural language processing. Unlike recurrent neural networks, Transformers process entire
sequences simultaneously using self-attention mechanisms.

Key components include:
- Multi-head self-attention: Allows the model to focus on different parts of the input
- Positional encoding: Provides sequence order information
- Feed-forward networks: Process attention outputs
- Layer normalization: Stabilizes training

Modern large language models like GPT, BERT, and T5 are all based on Transformer architectures.
The scalability of Transformers enables training on massive datasets with billions of parameters.
""",

    "quantum_computing_basics.txt": """
# Introduction to Quantum Computing

Quantum computing leverages quantum mechanical phenomena like superposition and entanglement
to perform computations. Unlike classical bits (0 or 1), quantum bits (qubits) can exist in
superposition states.

Fundamental principles:
- Superposition: Qubits can be in multiple states simultaneously
- Entanglement: Qubits can be correlated in ways impossible classically
- Quantum gates: Operations that manipulate qubit states
- Measurement: Collapses superposition to classical states

Quantum algorithms like Shor's (factoring) and Grover's (search) demonstrate exponential
speedups for specific problems. Current challenges include decoherence and error correction.
""",

    "neural_plasticity.txt": """
# Neural Plasticity and Learning

Neuroplasticity refers to the brain's ability to reorganize itself by forming new neural
connections. This fundamental property underlies learning, memory, and recovery from injury.

Types of plasticity:
- Synaptic plasticity: Changes in synapse strength
- Structural plasticity: Formation of new neural pathways
- Long-term potentiation (LTP): Persistent strengthening of synapses
- Long-term depression (LTD): Weakening of synaptic connections

Hebbian theory ("neurons that fire together wire together") explains how repeated activation
strengthens neural pathways. Modern research shows plasticity continues throughout life,
enabling continuous learning and adaptation.
""",

    "blockchain_consensus.txt": """
# Blockchain Consensus Mechanisms

Consensus mechanisms enable distributed networks to agree on a shared state without central
authority. Different approaches balance security, decentralization, and scalability.

Major consensus algorithms:
- Proof of Work (PoW): Computational puzzle solving (Bitcoin)
- Proof of Stake (PoS): Validator selection by token ownership (Ethereum 2.0)
- Practical Byzantine Fault Tolerance (PBFT): Vote-based consensus
- Delegated Proof of Stake (DPoS): Elected validators

Each mechanism addresses the Byzantine Generals Problem differently. Trade-offs include
energy consumption, centralization risks, and transaction throughput. Hybrid approaches
combine multiple mechanisms for optimized performance.
""",

    "renaissance_humanism.txt": """
# Renaissance Humanism and Art

Renaissance humanism emphasized human potential, classical learning, and rational inquiry.
This intellectual movement profoundly influenced art, architecture, and science from the
14th to 17th centuries.

Key characteristics:
- Classical revival: Study of Greek and Roman texts
- Human-centered worldview: Focus on individual achievement
- Perspective in art: Mathematical representation of 3D space
- Anatomical accuracy: Detailed study of human form

Artists like Leonardo da Vinci embodied humanist ideals, combining artistic mastery with
scientific investigation. The integration of mathematics, anatomy, and aesthetics created
unprecedented realism in painting and sculpture.
""",

    "gene_editing_crispr.txt": """
# CRISPR Gene Editing Technology

CRISPR-Cas9 enables precise modification of DNA sequences in living organisms. This
revolutionary tool has transformed molecular biology and holds promise for treating
genetic diseases.

CRISPR mechanism:
- Guide RNA directs Cas9 enzyme to target DNA sequence
- Cas9 makes double-strand break at specific location
- Cell's repair mechanisms modify the sequence
- Multiple edits can be made simultaneously

Applications include correcting disease-causing mutations, developing disease-resistant crops,
and creating animal models for research. Ethical considerations around human germline editing
remain subjects of ongoing debate.
""",

    "distributed_systems.txt": """
# Distributed Systems Architecture

Distributed systems coordinate multiple computers to achieve common goals. Key challenges
include maintaining consistency, handling failures, and achieving scalability.

Core concepts:
- CAP theorem: Consistency, Availability, Partition tolerance trade-offs
- Consensus protocols: Paxos, Raft for agreement
- Eventual consistency: Relaxed consistency for availability
- Sharding: Horizontal partitioning of data

Microservices architecture exemplifies modern distributed system design. Service meshes,
message queues, and distributed databases enable building resilient, scalable applications.
Observability through distributed tracing helps understand system behavior.
""",

    "computational_complexity.txt": """
# Computational Complexity Theory

Complexity theory classifies computational problems by resource requirements (time, space).
Understanding complexity guides algorithm design and problem-solving approaches.

Complexity classes:
- P: Problems solvable in polynomial time
- NP: Problems verifiable in polynomial time
- NP-Complete: Hardest problems in NP
- NP-Hard: At least as hard as NP-Complete problems

The P vs NP question asks whether every problem whose solution can be quickly verified
can also be quickly solved. This remains one of mathematics' greatest unsolved problems.
Practical implications affect cryptography, optimization, and artificial intelligence.
""",

    "dark_matter_cosmology.txt": """
# Dark Matter and Modern Cosmology

Dark matter comprises approximately 27% of the universe's mass-energy content. Though
invisible, its gravitational effects are observable through galaxy rotation curves and
gravitational lensing.

Evidence for dark matter:
- Galaxy rotation curves: Stars move faster than visible mass predicts
- Gravitational lensing: Light bends around invisible mass
- Cosmic microwave background: Patterns require dark matter
- Large-scale structure: Galaxy distribution needs dark matter

Leading candidates include WIMPs (Weakly Interacting Massive Particles) and axions.
Direct detection experiments search for dark matter particles, while astrophysical
observations constrain its properties.
""",

    "economic_game_theory.txt": """
# Game Theory in Economics

Game theory analyzes strategic interactions where outcomes depend on multiple actors'
decisions. Applications span economics, political science, and evolutionary biology.

Key concepts:
- Nash equilibrium: Stable strategy configurations
- Prisoner's dilemma: Individual vs collective rationality
- Zero-sum games: One player's gain equals another's loss
- Repeated games: Long-term cooperation strategies

Behavioral economics incorporates psychology into game-theoretic models. Real-world
applications include auction design, market regulation, and international negotiations.
Mechanism design uses game theory to engineer desired outcomes.
"""
}


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {'llamastack': {'url': 'http://llamastack.catalystlab-shared.svc.cluster.local:8321'}}


def upload_document(filename, content, llamastack_url):
    """Upload document to LLaMA Stack"""
    upload_url = f"{llamastack_url}/v1/vector_io/upload"

    files = {
        'file': (filename, content.encode('utf-8'), 'text/plain')
    }

    try:
        response = requests.post(upload_url, files=files, timeout=30)
        response.raise_for_status()
        return True, f"Uploaded {filename} ({len(content)} chars)"
    except Exception as e:
        return False, f"Failed to upload {filename}: {e}"


def main():
    print("Bulk Document Upload to LLaMA Stack")
    print("=" * 60)

    config = load_config()
    llamastack_url = config.get('llamastack', {}).get('url',
        'http://llamastack.catalystlab-shared.svc.cluster.local:8321')

    print(f"LLaMA Stack URL: {llamastack_url}")
    print(f"Documents to upload: {len(SAMPLE_DOCUMENTS)}")
    print()

    success_count = 0
    for filename, content in SAMPLE_DOCUMENTS.items():
        success, message = upload_document(filename, content, llamastack_url)
        print(f"  {message}")

        if success:
            success_count += 1

        time.sleep(1)  # Rate limiting

    print()
    print("=" * 60)
    print(f"Upload complete: {success_count}/{len(SAMPLE_DOCUMENTS)} successful")
    print()
    print("These documents will be:")
    print("  1. Chunked automatically by LLaMA Stack")
    print("  2. Embedded using Qwen3-Embedding-8B")
    print("  3. Stored in pgvector")
    print()
    print("Next step: Regenerate cortex visualization")
    print("  kubectl delete job golem-cortex-regenerate -n catalystlab-shared --ignore-not-found")
    print("  kubectl apply -f cortex-regenerate-job.yaml")


if __name__ == '__main__':
    main()
