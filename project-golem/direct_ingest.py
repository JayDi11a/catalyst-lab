#!/usr/bin/env python3
"""
Direct pgvector Ingestion
Creates embeddings and inserts directly into pgvector database.
This bypasses LLaMA Stack and gives us full control over the data.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

import psycopg2
import requests
import yaml
from pgvector.psycopg2 import register_vector


# Sample documents with categories
DOCUMENTS = [
    {
        "category": "AI & Machine Learning",
        "content": "Transformer architectures revolutionized NLP through self-attention mechanisms. Multi-head attention allows models to focus on different sequence positions simultaneously, enabling parallel processing unlike RNNs."
    },
    {
        "category": "AI & Machine Learning",
        "content": "Deep learning uses neural networks with multiple layers to learn hierarchical representations. Backpropagation and gradient descent optimize network weights through iterative training on large datasets."
    },
    {
        "category": "Quantum & Physics",
        "content": "Quantum superposition allows qubits to exist in multiple states simultaneously. This property, combined with entanglement, enables quantum computers to solve certain problems exponentially faster than classical computers."
    },
    {
        "category": "Quantum & Physics",
        "content": "The Heisenberg uncertainty principle states that position and momentum cannot be simultaneously measured with arbitrary precision. This fundamental limit reflects the wave-particle duality of quantum systems."
    },
    {
        "category": "Neuroscience & Cognition",
        "content": "Synaptic plasticity enables learning through strengthening or weakening of neural connections. Long-term potentiation (LTP) persistently enhances synaptic transmission following high-frequency stimulation."
    },
    {
        "category": "Neuroscience & Cognition",
        "content": "The prefrontal cortex mediates executive functions including working memory, decision-making, and cognitive control. Dopamine modulates prefrontal activity, influencing attention and goal-directed behavior."
    },
    {
        "category": "Cryptography & Security",
        "content": "Public-key cryptography uses mathematically related key pairs. Messages encrypted with the public key can only be decrypted with the private key, enabling secure communication without shared secrets."
    },
    {
        "category": "Cryptography & Security",
        "content": "Blockchain achieves consensus through proof-of-work mining. Miners compete to solve computational puzzles, with the winner adding the next block and earning rewards."
    },
    {
        "category": "Renaissance & Art",
        "content": "Linear perspective revolutionized Renaissance painting by creating the illusion of three-dimensional space on flat surfaces. Brunelleschi's mathematical approach influenced generations of artists."
    },
    {
        "category": "Renaissance & Art",
        "content": "Leonardo da Vinci exemplified Renaissance humanism, combining artistic mastery with scientific inquiry. His anatomical studies informed realistic human depiction in paintings like The Last Supper."
    },
    {
        "category": "Biology & Genetics",
        "content": "CRISPR-Cas9 enables precise DNA editing by guiding the Cas9 enzyme to target sequences. The system's programmability makes it a powerful tool for gene therapy and biotechnology."
    },
    {
        "category": "Biology & Genetics",
        "content": "Natural selection drives evolution through differential reproductive success. Organisms with advantageous traits are more likely to survive and pass those traits to offspring."
    },
    {
        "category": "Computer Science",
        "content": "The P versus NP problem asks whether every problem whose solution can be quickly verified can also be quickly solved. This fundamental question has profound implications for cryptography and optimization."
    },
    {
        "category": "Computer Science",
        "content": "Distributed systems must handle the CAP theorem's trade-offs between Consistency, Availability, and Partition tolerance. Network partitions force choosing between consistency and availability."
    },
    {
        "category": "Mathematics",
        "content": "Gödel's incompleteness theorems demonstrate fundamental limitations of formal systems. Any consistent axiomatic system powerful enough to describe arithmetic contains true statements that cannot be proven."
    },
    {
        "category": "Mathematics",
        "content": "Topology studies properties preserved under continuous deformations. Homeomorphisms define equivalence classes of topological spaces, abstracting geometric notions of shape."
    },
    {
        "category": "Robotics & Automation",
        "content": "SLAM (Simultaneous Localization and Mapping) enables robots to build maps while determining their location within them. Probabilistic approaches like particle filters handle sensor uncertainty."
    },
    {
        "category": "Robotics & Automation",
        "content": "Inverse kinematics calculates joint angles needed to achieve desired end-effector positions. Solutions may be non-unique, requiring optimization criteria for trajectory planning."
    },
    {
        "category": "Space & Astronomy",
        "content": "Dark energy comprises 68% of the universe's energy density and drives cosmic acceleration. Its nature remains mysterious, with the cosmological constant being the simplest explanation."
    },
    {
        "category": "Space & Astronomy",
        "content": "Black holes form when massive stars collapse, creating regions where gravity prevents even light from escaping. The event horizon marks the boundary of no return."
    },
    {
        "category": "Philosophy & Logic",
        "content": "Modal logic extends classical logic with operators for necessity and possibility. Possible worlds semantics provides an intuitive framework for interpreting modal statements."
    },
    {
        "category": "Philosophy & Logic",
        "content": "The mind-body problem questions how mental states relate to physical brain states. Dualism and physicalism represent competing metaphysical frameworks."
    },
    {
        "category": "History",
        "content": "The Industrial Revolution transformed manufacturing through mechanization and steam power. Factory systems replaced craft production, fundamentally altering economic and social structures."
    },
    {
        "category": "History",
        "content": "The Enlightenment emphasized reason, science, and individual rights. Philosophers like Locke and Rousseau influenced modern democratic political philosophy."
    },
    {
        "category": "Economics & Finance",
        "content": "Game theory analyzes strategic interactions where outcomes depend on multiple actors' decisions. Nash equilibrium identifies stable strategy profiles where no player benefits from unilateral deviation."
    },
    {
        "category": "Economics & Finance",
        "content": "Monetary policy influences economic activity through interest rate adjustments and money supply management. Central banks balance inflation control with employment objectives."
    },
    {
        "category": "Chemistry",
        "content": "Chemical bonds form through electron sharing or transfer between atoms. Covalent bonds involve shared electrons, while ionic bonds result from electron transfer creating charged ions."
    },
    {
        "category": "Chemistry",
        "content": "Catalysts increase reaction rates without being consumed. They lower activation energy by providing alternative reaction pathways with lower energy barriers."
    }
]


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("Error: config.yaml not found")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def connect_to_database(db_config):
    """Connect to pgvector database"""
    print("Connecting to pgvector...")
    try:
        password = os.environ.get('DB_PASSWORD', db_config.get('password', ''))
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=password
        )
        register_vector(conn)
        print(f"  Connected to {db_config['database']}")
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)


def get_embedding(text, embedding_url):
    """Get embedding from Qwen3-Embedding-8B"""
    try:
        # Ensure URL ends with /v1/embeddings
        url = embedding_url.rstrip('/')
        if not url.endswith('/v1/embeddings'):
            if url.endswith('/v1'):
                url = f"{url}/embeddings"
            else:
                url = f"{url}/v1/embeddings"

        response = requests.post(
            url,
            json={"input": text, "model": "Qwen/Qwen3-Embedding-8B"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    except Exception as e:
        print(f"  Error getting embedding: {e}")
        return None


def insert_vector(conn, table_name, doc_id, content, category, embedding):
    """Insert vector into pgvector table"""
    cursor = conn.cursor()

    document_json = {
        "chunk_id": doc_id,
        "content": content,
        "category": category,
        "metadata": {"source": "direct_ingest", "category": category}
    }

    try:
        cursor.execute(f"""
            INSERT INTO {table_name} (id, document, embedding, content_text)
            VALUES (%s, %s, %s, %s)
        """, (doc_id, json.dumps(document_json), embedding, content))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  Insert failed: {e}")
        return False


def main():
    print("Direct pgvector Ingestion")
    print("=" * 60)

    config = load_config()
    conn = connect_to_database(config['database'])

    # Find vector table
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name LIKE 'vs_vs_%' ORDER BY table_name LIMIT 1
    """)
    table_name = cursor.fetchone()[0]
    print(f"  Using table: {table_name}")

    embedding_url = config.get('embedding', {}).get('url',
        'http://qwen3-embedding-8b-kserve-workload-svc.kserve-lab.svc.cluster.local:8000/v1')

    print(f"  Embedding model: {embedding_url}")
    print(f"  Documents to add: {len(DOCUMENTS)}")
    print()

    success_count = 0
    for i, doc in enumerate(DOCUMENTS, 1):
        doc_id = str(uuid.uuid4())
        category = doc['category']
        content = doc['content']

        print(f"  [{i}/{len(DOCUMENTS)}] {category}: {content[:60]}...")

        embedding = get_embedding(content, embedding_url)
        if not embedding:
            continue

        if insert_vector(conn, table_name, doc_id, content, category, embedding):
            success_count += 1
            time.sleep(0.5)  # Rate limiting

    conn.close()

    print()
    print("=" * 60)
    print(f"Ingestion complete: {success_count}/{len(DOCUMENTS)} successful")
    print()
    print("Next: Regenerate cortex visualization")
    print("  kubectl delete job golem-cortex-regenerate -n catalystlab-shared --ignore-not-found")
    print("  kubectl apply -f cortex-regenerate-job.yaml")


if __name__ == '__main__':
    main()
