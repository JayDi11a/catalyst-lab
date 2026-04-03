#!/usr/bin/env python3
"""
Project Golem - Wikipedia Batch Ingestion
Fetches Wikipedia articles and ingests them via LLaMA Stack for embedding and storage.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict

import requests
import yaml


# Wikipedia articles organized by category (matching our visualization categories)
WIKIPEDIA_ARTICLES = {
    'AI & Machine Learning': [
        'Artificial_intelligence', 'Machine_learning', 'Deep_learning', 'Neural_network',
        'Convolutional_neural_network', 'Recurrent_neural_network', 'Transformer_(machine_learning)',
        'GPT-3', 'BERT_(language_model)', 'Natural_language_processing', 'Computer_vision',
        'Reinforcement_learning', 'Supervised_learning', 'Unsupervised_learning',
        'Transfer_learning', 'Generative_adversarial_network', 'Backpropagation',
        'Gradient_descent', 'Overfitting', 'Feature_extraction', 'Dimensionality_reduction'
    ],
    'Robotics & Automation': [
        'Robotics', 'Industrial_robot', 'Autonomous_robot', 'Mobile_robot',
        'Humanoid_robot', 'Robot_kinematics', 'Robot_control', 'SLAM_(navigation)',
        'Path_planning', 'Robot_sensor', 'Actuator', 'End_effector',
        'Inverse_kinematics', 'Motion_planning', 'Swarm_robotics'
    ],
    'Quantum & Physics': [
        'Quantum_mechanics', 'Quantum_computing', 'Quantum_entanglement', 'Superposition',
        'Quantum_algorithm', 'Quantum_cryptography', 'Quantum_teleportation',
        'Schrodinger_equation', 'Heisenberg_uncertainty_principle', 'Wave_function',
        'Quantum_field_theory', 'String_theory', 'General_relativity', 'Special_relativity',
        'Particle_physics', 'Standard_Model', 'Higgs_boson', 'Dark_matter', 'Dark_energy'
    ],
    'Neuroscience & Cognition': [
        'Neuroscience', 'Cognitive_science', 'Brain', 'Neuron', 'Synapse',
        'Neuroplasticity', 'Memory', 'Consciousness', 'Perception', 'Attention',
        'Learning', 'Emotion', 'Decision-making', 'Cognitive_neuroscience',
        'Computational_neuroscience', 'Neural_coding', 'Brain-computer_interface'
    ],
    'Space & Astronomy': [
        'Astronomy', 'Astrophysics', 'Cosmology', 'Solar_System', 'Planet',
        'Star', 'Galaxy', 'Black_hole', 'Neutron_star', 'Supernova',
        'Big_Bang', 'Universe', 'Milky_Way', 'Exoplanet', 'Space_exploration',
        'International_Space_Station', 'Mars_rover', 'James_Webb_Space_Telescope'
    ],
    'Cryptography & Security': [
        'Cryptography', 'Encryption', 'Public-key_cryptography', 'RSA_(cryptosystem)',
        'Blockchain', 'Bitcoin', 'Cryptocurrency', 'Digital_signature',
        'Hash_function', 'Secure_Hash_Algorithms', 'Advanced_Encryption_Standard',
        'Computer_security', 'Cybersecurity', 'Network_security', 'Authentication'
    ],
    'Renaissance & Art': [
        'Renaissance', 'Leonardo_da_Vinci', 'Michelangelo', 'Raphael',
        'Italian_Renaissance', 'Renaissance_art', 'Renaissance_architecture',
        'Humanism', 'Perspective_(graphical)', 'Sfumato', 'Contrapposto',
        'The_Last_Supper_(Leonardo)', 'Mona_Lisa', 'Sistine_Chapel_ceiling'
    ],
    'Biology & Genetics': [
        'Biology', 'Genetics', 'DNA', 'RNA', 'Gene', 'Genome',
        'Evolution', 'Natural_selection', 'Cell_(biology)', 'Protein',
        'Enzyme', 'Metabolism', 'Photosynthesis', 'CRISPR', 'Gene_editing',
        'Molecular_biology', 'Microbiology', 'Ecology', 'Biodiversity'
    ],
    'Computer Science': [
        'Computer_science', 'Algorithm', 'Data_structure', 'Complexity_theory',
        'Computational_complexity_theory', 'P_versus_NP_problem', 'Turing_machine',
        'Lambda_calculus', 'Programming_language', 'Compiler', 'Operating_system',
        'Database', 'Computer_network', 'Internet', 'World_Wide_Web',
        'Software_engineering', 'Version_control', 'Git'
    ],
    'Mathematics': [
        'Mathematics', 'Calculus', 'Linear_algebra', 'Differential_equation',
        'Topology', 'Abstract_algebra', 'Number_theory', 'Discrete_mathematics',
        'Graph_theory', 'Combinatorics', 'Probability_theory', 'Statistics',
        'Numerical_analysis', 'Optimization_(mathematics)', 'Game_theory',
        'Information_theory', 'Category_theory', 'Set_theory'
    ],
    'Philosophy & Logic': [
        'Philosophy', 'Logic', 'Epistemology', 'Metaphysics', 'Ethics',
        'Ontology', 'Phenomenology_(philosophy)', 'Existentialism', 'Rationalism',
        'Empiricism', 'Philosophy_of_mind', 'Philosophy_of_science',
        'Formal_logic', 'Propositional_calculus', 'Predicate_logic', 'Modal_logic'
    ],
    'History': [
        'History', 'Ancient_history', 'Classical_antiquity', 'Middle_Ages',
        'Age_of_Enlightenment', 'Industrial_Revolution', 'World_War_I',
        'World_War_II', 'Cold_War', 'Ancient_Greece', 'Ancient_Rome',
        'Ancient_Egypt', 'Byzantine_Empire', 'Ottoman_Empire', 'British_Empire'
    ],
    'Economics & Finance': [
        'Economics', 'Microeconomics', 'Macroeconomics', 'Supply_and_demand',
        'Market_economy', 'Capitalism', 'Keynesian_economics', 'Game_theory',
        'Behavioral_economics', 'Financial_market', 'Stock_market', 'Cryptocurrency',
        'Central_bank', 'Monetary_policy', 'Fiscal_policy'
    ],
    'Chemistry': [
        'Chemistry', 'Organic_chemistry', 'Inorganic_chemistry', 'Physical_chemistry',
        'Biochemistry', 'Chemical_bond', 'Molecule', 'Atom', 'Periodic_table',
        'Chemical_reaction', 'Catalysis', 'Electrochemistry', 'Thermodynamics',
        'Quantum_chemistry', 'Polymer', 'Nanotechnology'
    ]
}


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("Error: config.yaml not found")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def fetch_wikipedia_article(article_title: str) -> Dict:
    """Fetch Wikipedia article content via MediaWiki API"""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'titles': article_title,
        'prop': 'extracts',
        'explaintext': True,
        'exsectionformat': 'plain'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data['query']['pages']
        page = next(iter(pages.values()))

        if 'missing' in page:
            return None

        return {
            'title': page.get('title', article_title),
            'content': page.get('extract', ''),
            'pageid': page.get('pageid')
        }
    except Exception as e:
        print(f"  Warning: Failed to fetch {article_title}: {e}")
        return None


def upload_to_llamastack(article: Dict, category: str, config: dict) -> bool:
    """Upload article to LLaMA Stack for embedding and storage"""
    llamastack_url = config.get('llamastack', {}).get('url', 'http://localhost:8321')

    # Format document for LLaMA Stack
    document_content = f"# {article['title']}\n\nCategory: {category}\n\n{article['content']}"

    try:
        # Upload document to LLaMA Stack
        upload_url = f"{llamastack_url}/v1/vector_io/upload"
        files = {
            'file': (f"{article['title']}.txt", document_content.encode('utf-8'), 'text/plain')
        }

        response = requests.post(upload_url, files=files, timeout=30)
        response.raise_for_status()

        print(f"  Uploaded: {article['title']} ({len(article['content'])} chars)")
        return True

    except Exception as e:
        print(f"  Error uploading {article['title']}: {e}")
        return False


def main():
    print("Wikipedia Batch Ingestion for Project Golem")
    print("=" * 60)

    config = load_config()

    total_articles = sum(len(articles) for articles in WIKIPEDIA_ARTICLES.values())
    print(f"Preparing to ingest {total_articles} Wikipedia articles across {len(WIKIPEDIA_ARTICLES)} categories")
    print()

    ingested_count = 0
    failed_count = 0

    for category, article_titles in WIKIPEDIA_ARTICLES.items():
        print(f"\n{category} ({len(article_titles)} articles)")
        print("-" * 60)

        for title in article_titles:
            # Fetch Wikipedia article
            article = fetch_wikipedia_article(title)

            if not article or not article['content']:
                print(f"  Skipped: {title} (no content)")
                failed_count += 1
                continue

            # Upload to LLaMA Stack
            if upload_to_llamastack(article, category, config):
                ingested_count += 1
            else:
                failed_count += 1

            # Rate limiting - be nice to Wikipedia and LLaMA Stack
            time.sleep(1)

    print()
    print("=" * 60)
    print(f"Ingestion complete!")
    print(f"  Success: {ingested_count}/{total_articles}")
    print(f"  Failed: {failed_count}/{total_articles}")
    print()
    print("Next step: Run ingest.py to regenerate the 3D cortex visualization")
    print("  kubectl exec -n catalystlab-shared <pod-name> -- python ingest.py")


if __name__ == '__main__':
    main()
