#!/usr/bin/env python3
"""
Direct pgvector Ingestion - 180 Documents
Expanded dataset for denser neural memory visualization.
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

# 180 documents across 20 categories (9 per category)
DOCUMENTS = [
    # AI & Machine Learning (9 docs)
    {"category": "AI & Machine Learning", "content": "Transformer architectures revolutionized NLP through self-attention mechanisms enabling parallel processing of sequences."},
    {"category": "AI & Machine Learning", "content": "Deep learning hierarchical representations emerge from multiple neural network layers trained with backpropagation."},
    {"category": "AI & Machine Learning", "content": "Convolutional neural networks achieve state-of-the-art image recognition through learned spatial feature hierarchies."},
    {"category": "AI & Machine Learning", "content": "Reinforcement learning optimizes policies through trial-and-error interaction with environments using reward signals."},
    {"category": "AI & Machine Learning", "content": "Generative Adversarial Networks produce realistic synthetic data through adversarial generator-discriminator training."},
    {"category": "AI & Machine Learning", "content": "Transfer learning applies pre-trained model knowledge to new tasks with limited domain-specific data."},
    {"category": "AI & Machine Learning", "content": "Attention mechanisms dynamically weight input features allowing models to focus on relevant information."},
    {"category": "AI & Machine Learning", "content": "Explainable AI methods like SHAP values provide interpretability insights into black-box model predictions."},
    {"category": "AI & Machine Learning", "content": "Federated learning trains distributed models while preserving data privacy across decentralized devices."},

    # Quantum & Physics (9 docs)
    {"category": "Quantum & Physics", "content": "Quantum superposition enables qubits to exist in multiple states simultaneously unlike classical bits."},
    {"category": "Quantum & Physics", "content": "Heisenberg uncertainty principle fundamentally limits simultaneous measurement precision of complementary variables."},
    {"category": "Quantum & Physics", "content": "Quantum entanglement creates non-local correlations between particles violating classical hidden variable theories."},
    {"category": "Quantum & Physics", "content": "Quantum tunneling allows particles to penetrate classically forbidden potential barriers through wave properties."},
    {"category": "Quantum & Physics", "content": "Bell's theorem proves quantum mechanics incompatible with local realism through inequality violations."},
    {"category": "Quantum & Physics", "content": "The Standard Model unifies electromagnetic, weak, and strong forces through gauge field theories."},
    {"category": "Quantum & Physics", "content": "String theory proposes vibrating one-dimensional strings as fundamental entities replacing point particles."},
    {"category": "Quantum & Physics", "content": "Quantum error correction protects fragile qubit states from decoherence using redundant encoding schemes."},
    {"category": "Quantum & Physics", "content": "Bose-Einstein condensates demonstrate macroscopic quantum phenomena when bosons occupy identical ground states."},

    # Neuroscience & Cognition (9 docs)
    {"category": "Neuroscience & Cognition", "content": "Synaptic plasticity strengthens or weakens neural connections underlying learning and memory formation."},
    {"category": "Neuroscience & Cognition", "content": "Prefrontal cortex executive functions coordinate working memory, decision-making, and cognitive control."},
    {"category": "Neuroscience & Cognition", "content": "Neuroplasticity reorganizes brain structure through formation of new neural connections across lifespan."},
    {"category": "Neuroscience & Cognition", "content": "Mirror neurons fire during both action execution and observation supporting imitation and empathy."},
    {"category": "Neuroscience & Cognition", "content": "Hippocampus consolidates declarative memories and maintains spatial cognitive maps through place cells."},
    {"category": "Neuroscience & Cognition", "content": "Neurotransmitter systems modulate mood, motivation, and cognition with imbalances causing disorders."},
    {"category": "Neuroscience & Cognition", "content": "Default mode network activates during rest and self-referential thought showing dysregulation in depression."},
    {"category": "Neuroscience & Cognition", "content": "Predictive coding frameworks model perception as hierarchical Bayesian inference minimizing prediction errors."},
    {"category": "Neuroscience & Cognition", "content": "Sleep consolidates memories through synaptic homeostasis and neural activity replay during REM cycles."},

    # Cryptography & Security (9 docs)
    {"category": "Cryptography & Security", "content": "Public-key cryptography enables secure communication through mathematically related encryption and decryption keys."},
    {"category": "Cryptography & Security", "content": "Blockchain consensus mechanisms like proof-of-work ensure decentralized agreement without trusted authorities."},
    {"category": "Cryptography & Security", "content": "Zero-knowledge proofs verify statements without revealing underlying secret information enabling privacy."},
    {"category": "Cryptography & Security", "content": "Cryptographic hash functions create collision-resistant one-way digests anchoring digital signatures and blockchains."},
    {"category": "Cryptography & Security", "content": "Elliptic curve cryptography provides equivalent security to RSA with dramatically smaller key sizes."},
    {"category": "Cryptography & Security", "content": "Homomorphic encryption enables computation on encrypted data without decryption preserving confidentiality."},
    {"category": "Cryptography & Security", "content": "Multi-party computation allows collaborative analysis while maintaining individual input privacy through protocols."},
    {"category": "Cryptography & Security", "content": "Post-quantum cryptography develops algorithms resistant to quantum computer cryptanalytic attacks."},
    {"category": "Cryptography & Security", "content": "Differential privacy adds calibrated noise protecting individual records in statistical datasets."},

    # Renaissance & Art (9 docs)
    {"category": "Renaissance & Art", "content": "Linear perspective mathematically creates three-dimensional depth illusion on two-dimensional painting surfaces."},
    {"category": "Renaissance & Art", "content": "Leonardo da Vinci synthesized artistic mastery with scientific inquiry epitomizing Renaissance humanism ideals."},
    {"category": "Renaissance & Art", "content": "Michelangelo's Sistine Chapel frescoes demonstrate anatomical precision and divine inspiration at monumental scale."},
    {"category": "Renaissance & Art", "content": "Sfumato technique creates atmospheric depth through subtle tonal gradations blurring edges softly."},
    {"category": "Renaissance & Art", "content": "Raphael's School of Athens harmoniously composes classical philosophy within illusionistic architectural space."},
    {"category": "Renaissance & Art", "content": "Oil painting techniques enabled unprecedented luminosity and detail in Northern European altarpieces."},
    {"category": "Renaissance & Art", "content": "Chiaroscuro dramatic lighting creates sculptural volume through strong light-dark contrasts in paintings."},
    {"category": "Renaissance & Art", "content": "Botticelli's mythological works revive classical antiquity with Neo-Platonic symbolism and flowing grace."},
    {"category": "Renaissance & Art", "content": "Dürer's prints disseminated Renaissance ideas through technically virtuosic engravings and woodcuts."},

    # Biology & Genetics (9 docs)
    {"category": "Biology & Genetics", "content": "CRISPR-Cas9 gene editing precisely targets DNA sequences enabling therapeutic and biotechnology applications."},
    {"category": "Biology & Genetics", "content": "Natural selection drives evolution through differential reproductive success of organisms with advantageous traits."},
    {"category": "Biology & Genetics", "content": "DNA replication proceeds semi-conservatively with complementary base pairing ensuring genetic information fidelity."},
    {"category": "Biology & Genetics", "content": "Gene expression regulation involves transcription factors and epigenetic modifications controlling accessibility."},
    {"category": "Biology & Genetics", "content": "RNA interference silences genes through small RNA molecules targeting complementary messenger RNA sequences."},
    {"category": "Biology & Genetics", "content": "Mendelian inheritance patterns explain trait transmission through independent allele segregation during reproduction."},
    {"category": "Biology & Genetics", "content": "Mitochondrial DNA maternal inheritance enables molecular clock dating of evolutionary lineages."},
    {"category": "Biology & Genetics", "content": "Horizontal gene transfer rapidly spreads traits like antibiotic resistance among bacteria outside reproduction."},
    {"category": "Biology & Genetics", "content": "Alternative splicing generates multiple protein isoforms from single genes expanding proteomic diversity."},

    # Computer Science (9 docs)
    {"category": "Computer Science", "content": "P versus NP problem asks whether quickly verifiable solutions can also be quickly found computationally."},
    {"category": "Computer Science", "content": "CAP theorem forces distributed systems to trade off consistency, availability, and partition tolerance."},
    {"category": "Computer Science", "content": "Dynamic programming optimizes problems by memoizing overlapping subproblem solutions avoiding redundant computation."},
    {"category": "Computer Science", "content": "Binary search trees enable efficient ordered operations with balanced variants guaranteeing logarithmic performance."},
    {"category": "Computer Science", "content": "Hash tables provide average constant-time lookup through key hashing with collision resolution strategies."},
    {"category": "Computer Science", "content": "Functional programming treats computation as mathematical function evaluation without mutable state side effects."},
    {"category": "Computer Science", "content": "Garbage collection automates memory management by reclaiming unreachable objects during program execution."},
    {"category": "Computer Science", "content": "MapReduce processes massive datasets by mapping operations to partitions then reducing aggregated results."},
    {"category": "Computer Science", "content": "Consensus algorithms like Paxos enable distributed agreement despite node failures and network partitions."},

    # Mathematics (9 docs)
    {"category": "Mathematics", "content": "Gödel's incompleteness theorems prove fundamental limitations in formal axiomatic mathematical systems."},
    {"category": "Mathematics", "content": "Topology studies properties preserved under continuous deformations defining equivalence through homeomorphisms."},
    {"category": "Mathematics", "content": "Group theory captures symmetry through sets with associative binary operations forming algebraic structures."},
    {"category": "Mathematics", "content": "Calculus quantifies change through derivatives and accumulation through integrals in fundamental reciprocity."},
    {"category": "Mathematics", "content": "Prime numbers contain no divisors except unity and themselves with distribution described asymptotically."},
    {"category": "Mathematics", "content": "Complex numbers extend reals with imaginary unit connecting exponentials and trigonometry elegantly."},
    {"category": "Mathematics", "content": "Linear algebra analyzes vector spaces through transformations revealing eigenvalue invariant structures."},
    {"category": "Mathematics", "content": "Differential equations model dynamic systems relating functions to their rates of change."},
    {"category": "Mathematics", "content": "Probability theory quantifies uncertainty through measure on event spaces enabling Bayesian inference."},

    # Robotics & Automation (9 docs)
    {"category": "Robotics & Automation", "content": "SLAM simultaneously localizes robots while mapping unknown environments through probabilistic filtering."},
    {"category": "Robotics & Automation", "content": "Inverse kinematics calculates joint angles achieving desired end-effector positions for manipulation."},
    {"category": "Robotics & Automation", "content": "PID controllers regulate systems through proportional, integral, and derivative error feedback terms."},
    {"category": "Robotics & Automation", "content": "Computer vision extracts actionable information from images enabling robotic perception and recognition."},
    {"category": "Robotics & Automation", "content": "Motion planning finds collision-free paths through configuration space using sampling-based algorithms."},
    {"category": "Robotics & Automation", "content": "Force control enables compliant robot interaction with uncertain environments through impedance regulation."},
    {"category": "Robotics & Automation", "content": "Sensor fusion combines multi-modal measurements optimally estimating state through Kalman filtering."},
    {"category": "Robotics & Automation", "content": "Grasp planning considers contact forces and friction cones ensuring stable object manipulation."},
    {"category": "Robotics & Automation", "content": "Swarm robotics coordinates many simple robots producing emergent collective behaviors decentrally."},

    # Space & Astronomy (9 docs)
    {"category": "Space & Astronomy", "content": "Dark energy comprises most universal energy density driving cosmic acceleration through unknown mechanisms."},
    {"category": "Space & Astronomy", "content": "Black holes form from stellar collapse creating regions where gravity prevents light escape."},
    {"category": "Space & Astronomy", "content": "Gravitational waves ripple spacetime from accelerating masses confirmed by interferometric detection."},
    {"category": "Space & Astronomy", "content": "Cosmic microwave background reveals early universe conditions seeding large-scale structure formation."},
    {"category": "Space & Astronomy", "content": "Exoplanets orbit distant stars detected through transit photometry and radial velocity methods."},
    {"category": "Space & Astronomy", "content": "Neutron stars compress stellar mass into city-sized spheres emitting beamed pulsar radiation."},
    {"category": "Space & Astronomy", "content": "Stellar nucleosynthesis forges heavy elements in cores and supernova explosions enriching galaxies."},
    {"category": "Space & Astronomy", "content": "Dark matter outweighs visible matter yet remains undetected except through gravitational effects."},
    {"category": "Space & Astronomy", "content": "Hubble's law relates galaxy recession velocities to distances revealing cosmic expansion rate."},

    # Philosophy & Logic (9 docs)
    {"category": "Philosophy & Logic", "content": "Modal logic extends classical logic with necessity and possibility operators using possible worlds semantics."},
    {"category": "Philosophy & Logic", "content": "Mind-body problem questions mental state relationships to physical brain processes in consciousness."},
    {"category": "Philosophy & Logic", "content": "Epistemology studies knowledge nature and scope examining justified true belief conditions."},
    {"category": "Philosophy & Logic", "content": "Utilitarianism judges actions by consequences for overall happiness in consequentialist ethics."},
    {"category": "Philosophy & Logic", "content": "Kant's categorical imperative grounds morality in universal rational principles in deontological framework."},
    {"category": "Philosophy & Logic", "content": "Existentialism emphasizes individual freedom, authentic choice, and self-determined essence."},
    {"category": "Philosophy & Logic", "content": "Logical positivism demanded empirical verifiability for meaningful statements in analytic tradition."},
    {"category": "Philosophy & Logic", "content": "Free will debates whether choices are causally determined or allow genuine agency."},
    {"category": "Philosophy & Logic", "content": "Phenomenology studies conscious experience from first-person perspective bracketing presuppositions."},

    # History (9 docs)
    {"category": "History", "content": "Industrial Revolution mechanized production through steam power fundamentally transforming societies."},
    {"category": "History", "content": "Enlightenment emphasized reason, science, and rights influencing modern democratic philosophy."},
    {"category": "History", "content": "French Revolution overthrew monarchy establishing republican principles through radical transformation."},
    {"category": "History", "content": "Printing press democratized knowledge accelerating Renaissance and Reformation through mass literacy."},
    {"category": "History", "content": "World War I's industrial warfare destroyed empires reshaping global geopolitical order."},
    {"category": "History", "content": "Black Death killed one-third of Europeans weakening feudalism through labor shortages."},
    {"category": "History", "content": "Columbus's voyage initiated sustained Old-New World contact transforming global ecology."},
    {"category": "History", "content": "Roman Empire's legal and Latin legacy influenced Western civilization for millennia."},
    {"category": "History", "content": "Scientific Revolution replaced Aristotelian philosophy with experimental method and mathematics."},

    # Economics & Finance (9 docs)
    {"category": "Economics & Finance", "content": "Game theory analyzes strategic interactions identifying Nash equilibrium stable strategy profiles."},
    {"category": "Economics & Finance", "content": "Monetary policy influences activity through interest rates and money supply balancing inflation employment."},
    {"category": "Economics & Finance", "content": "Comparative advantage explains trade gains from specialization even with absolute efficiency differences."},
    {"category": "Economics & Finance", "content": "Market failures occur from externalities, public goods, and information asymmetries justifying intervention."},
    {"category": "Economics & Finance", "content": "Efficient market hypothesis claims prices fully reflect available information in various forms."},
    {"category": "Economics & Finance", "content": "Options provide rights without obligations valued through Black-Scholes arbitrage-free pricing."},
    {"category": "Economics & Finance", "content": "Supply and demand curves determine equilibrium prices through market clearing mechanisms."},
    {"category": "Economics & Finance", "content": "Fiscal policy uses government spending and taxation for countercyclical macroeconomic stabilization."},
    {"category": "Economics & Finance", "content": "Moral hazard reduces risk avoidance when insurance protects against consequences."},

    # Chemistry (9 docs)
    {"category": "Chemistry", "content": "Chemical bonds form through electron sharing in covalent bonds or transfer in ionic bonds."},
    {"category": "Chemistry", "content": "Catalysts accelerate reactions by lowering activation energy without being consumed."},
    {"category": "Chemistry", "content": "Periodic table organizes elements by atomic number revealing recurring chemical property patterns."},
    {"category": "Chemistry", "content": "Acid-base reactions transfer protons between species with pH measuring hydrogen ion concentration."},
    {"category": "Chemistry", "content": "Thermodynamics determines reaction spontaneity through Gibbs free energy combining enthalpy entropy."},
    {"category": "Chemistry", "content": "Electrochemistry interconverts chemical and electrical energy in batteries and fuel cells."},
    {"category": "Chemistry", "content": "Molecular orbital theory describes bonding through wave function overlap creating orbital combinations."},
    {"category": "Chemistry", "content": "Spectroscopy identifies molecules through electromagnetic radiation interaction revealing structure."},
    {"category": "Chemistry", "content": "Equilibrium constants relate concentrations at equilibrium with Le Chatelier predicting shifts."},

    # Climate & Environment (9 docs)
    {"category": "Climate & Environment", "content": "Greenhouse gases trap infrared radiation warming Earth's surface through atmospheric absorption."},
    {"category": "Climate & Environment", "content": "Ocean acidification from CO2 absorption threatens marine organisms with calcium carbonate shells."},
    {"category": "Climate & Environment", "content": "Deforestation reduces carbon sequestration disrupting water cycles and biodiversity."},
    {"category": "Climate & Environment", "content": "Renewable energy from solar, wind, and hydro provides sustainable fossil fuel alternatives."},
    {"category": "Climate & Environment", "content": "Biodiversity loss accelerates through habitat destruction threatening ecosystem services."},
    {"category": "Climate & Environment", "content": "Carbon cycle exchanges CO2 between atmosphere, oceans, and biosphere disrupted by emissions."},
    {"category": "Climate & Environment", "content": "Permafrost thawing releases methane and CO2 in positive feedback amplifying warming."},
    {"category": "Climate & Environment", "content": "Sustainable agriculture balances food production with environmental protection through practices."},
    {"category": "Climate & Environment", "content": "Water scarcity affects billions through aquifer depletion intensified by climate change."},

    # Medicine & Healthcare (9 docs)
    {"category": "Medicine & Healthcare", "content": "Antibiotics target bacterial processes like cell walls and protein synthesis fighting infections."},
    {"category": "Medicine & Healthcare", "content": "Vaccines prime immune recognition of pathogens without disease enabling herd immunity."},
    {"category": "Medicine & Healthcare", "content": "Cancer arises from mutations disrupting growth control in oncogenes and tumor suppressors."},
    {"category": "Medicine & Healthcare", "content": "Diabetes involves insulin deficiency or resistance disrupting glucose metabolism regulation."},
    {"category": "Medicine & Healthcare", "content": "Cardiovascular disease causes most deaths through atherosclerosis narrowing arteries."},
    {"category": "Medicine & Healthcare", "content": "Immunotherapy harnesses immune systems against cancer through checkpoint inhibitor treatments."},
    {"category": "Medicine & Healthcare", "content": "Human microbiome influences health from digestion to immunity with dysbiosis causing disease."},
    {"category": "Medicine & Healthcare", "content": "Precision medicine tailors treatments to genetic profiles through pharmacogenomic predictions."},
    {"category": "Medicine & Healthcare", "content": "Neurodegenerative diseases involve protein aggregation damaging neurons progressively."},

    # Linguistics & Language (9 docs)
    {"category": "Linguistics & Language", "content": "Universal grammar proposes innate language capacity with recursive syntax biologically endowed."},
    {"category": "Linguistics & Language", "content": "Phonology studies sound patterns with phonemes distinguishing meaning and allophones varying."},
    {"category": "Linguistics & Language", "content": "Morphology examines word structure from roots and affixes with agglutinative combining."},
    {"category": "Linguistics & Language", "content": "Syntax governs sentence structure through hierarchical phrase organization in constituency trees."},
    {"category": "Linguistics & Language", "content": "Semantics studies meaning from word senses to compositional interpretation in formal logic."},
    {"category": "Linguistics & Language", "content": "Pragmatics examines language use beyond literal meaning through conversational implicature."},
    {"category": "Linguistics & Language", "content": "Language acquisition proceeds through universal developmental stages in critical periods."},
    {"category": "Linguistics & Language", "content": "Sociolinguistics studies variation across social groups through dialects and registers."},
    {"category": "Linguistics & Language", "content": "Historical linguistics reconstructs evolution through comparative method identifying cognates."},

    # Music & Acoustics (9 docs)
    {"category": "Music & Acoustics", "content": "Harmonic series defines overtones above fundamentals with integer ratios creating consonance."},
    {"category": "Music & Acoustics", "content": "Fourier analysis decomposes waveforms into sinusoids with harmonic spectra determining timbre."},
    {"category": "Music & Acoustics", "content": "Equal temperament divides octaves into twelve equal semitones enabling key modulation."},
    {"category": "Music & Acoustics", "content": "Rhythm organizes sound in time through meter with polyrhythms layering patterns."},
    {"category": "Music & Acoustics", "content": "Counterpoint combines independent melodies following harmonic rules in polyphonic texture."},
    {"category": "Music & Acoustics", "content": "Sound localization uses interaural differences with precedence effect assigning direction."},
    {"category": "Music & Acoustics", "content": "Resonance amplifies specific frequencies in instruments through strings, air columns, membranes."},
    {"category": "Music & Acoustics", "content": "Digital audio sampling discretizes signals at rates exceeding twice maximum frequency."},
    {"category": "Music & Acoustics", "content": "Music cognition studies neural processing with absolute pitch representing extreme ability."},

    # Materials Science (9 docs)
    {"category": "Materials Science", "content": "Crystal structures arrange atoms in periodic lattices determining material properties."},
    {"category": "Materials Science", "content": "Phase diagrams map material states across temperature and composition showing transitions."},
    {"category": "Materials Science", "content": "Dislocations enable plastic deformation in crystals through line defect motion."},
    {"category": "Materials Science", "content": "Composite materials combine constituents for superior properties like strength-to-weight ratios."},
    {"category": "Materials Science", "content": "Semiconductors have intermediate conductivity with doping creating p-type and n-type materials."},
    {"category": "Materials Science", "content": "Glass transition describes amorphous materials changing from brittle to rubbery states."},
    {"category": "Materials Science", "content": "Corrosion degrades metals through electrochemical reactions prevented by passivation."},
    {"category": "Materials Science", "content": "Nanomaterials exhibit novel properties at atomic scales enabling revolutionary applications."},
    {"category": "Materials Science", "content": "Ceramics are inorganic non-metals with high hardness and melting points."},

    # Psychology & Behavior (9 docs)
    {"category": "Psychology & Behavior", "content": "Classical conditioning associates neutral stimuli with reflexive responses through temporal pairing."},
    {"category": "Psychology & Behavior", "content": "Operant conditioning shapes behavior through reinforcement and punishment consequences."},
    {"category": "Psychology & Behavior", "content": "Cognitive dissonance creates discomfort from conflicting beliefs motivating attitude change."},
    {"category": "Psychology & Behavior", "content": "Working memory holds limited information temporarily with phonological and visuospatial components."},
    {"category": "Psychology & Behavior", "content": "Attachment theory describes infant bonding patterns predicting social emotional outcomes."},
    {"category": "Psychology & Behavior", "content": "Social learning occurs through observation and imitation of modeled behaviors."},
    {"category": "Psychology & Behavior", "content": "Personality traits like Big Five dimensions describe stable individual differences."},
    {"category": "Psychology & Behavior", "content": "Cognitive biases systematically distort judgment through heuristics like availability and anchoring."},
    {"category": "Psychology & Behavior", "content": "Developmental stages describe psychological changes across lifespan in cognitive abilities."}
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
    print("Direct pgvector Ingestion - 180 Documents Across 20 Categories")
    print("=" * 60)

    config = load_config()
    conn = connect_to_database(config['database'])

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
            time.sleep(0.2)  # Rate limiting

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
