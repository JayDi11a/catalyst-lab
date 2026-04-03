# Project Golem: Neural Memory Visualizer

**A 3D interface for visualizing RAG (Retrieval-Augmented Generation) memory structures in real-time using the AI Catalyst Lab stack.**

This is an adapted implementation of [Project Golem](https://github.com/JayDi11a/Project_Golem) that integrates with the catalyst-lab infrastructure:
- **Embeddings**: Qwen3-Embedding-8B (4096 dimensions)
- **Vector Database**: pgvector (PostgreSQL)
- **RAG Pipeline**: LLaMA Stack

**Namespace:** Can run locally or deploy to `catalystlab-shared`

## Overview

Project Golem visualizes semantic space by projecting high-dimensional embeddings down to an interactive 3D "cortex." Instead of treating the vector database as a black box, Golem allows you to see how your AI's memory is structured and watch it "light up" specific neural pathways when responding to queries.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Project Golem Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  pgvector (vectordb)                                         │
│  ↓ [Fetch 4096d vectors]                                     │
│  ↓                                                            │
│  UMAP Dimensionality Reduction (4096d → 3d)                  │
│  ↓                                                            │
│  golem_cortex.json + KNN connections                         │
│  ↓                                                            │
│  ┌──────────────────┬──────────────────────────┐             │
│  ↓                  ↓                          ↓             │
│  Three.js      Flask Server          Query Pipeline         │
│  (WebGL)       (localhost:8000)                              │
│                                      ↓                        │
│                          User Query → Qwen3-Embedding-8B     │
│                                      ↓                        │
│                          pgvector similarity search          │
│                                      ↓                        │
│                          Highlight matching nodes            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Ingest Phase** (`ingest.py`):
   - Connects to pgvector database (`vectordb` in `catalystlab-shared`)
   - Fetches all existing vectors stored by LLaMA Stack
   - Applies UMAP to reduce 4096 dimensions → 3D coordinates
   - Builds KNN graph to find semantic connections
   - Saves visualization data to `golem_cortex.json`

2. **Visualization Phase** (`GolemServer.py`):
   - Serves Three.js frontend on port 8000
   - Handles user queries via Qwen3-Embedding-8B endpoint
   - Performs similarity search against pgvector
   - Returns matched vectors for highlighting in 3D space

## Prerequisites

### Required Services

The following services must be running in the cluster:

| Service | Namespace | Verification Command |
|---------|-----------|---------------------|
| PostgreSQL + pgvector | `catalystlab-shared` | `kubectl get cluster -n catalystlab-shared pgvector-cluster` |
| Qwen3-Embedding-8B | `kserve-lab` | `kubectl get pods -n kserve-lab -l serving.kserve.io/inferenceservice=qwen3-embedding-8b` |

Verify pgvector has data:

```bash
kubectl exec -n catalystlab-shared pgvector-cluster-1 -- \
  psql -U vectordb -d vectordb \
  -c "SELECT COUNT(*) FROM vectors;"
```

Expected: At least 1 row. If empty, use LLaMA Stack to ingest documents first.

### Local Development Requirements

- Python 3.10+
- `kubectl` configured with cluster access
- Port-forwarding access to cluster services (or use external endpoints)

### Python Dependencies

Install via `uv` (recommended) or `pip`:

```bash
uv pip install -r requirements.txt
```

## Installation

### Option 1: Local Development (Recommended for Testing)

#### 1. Set up port forwarding

Forward pgvector to localhost:

```bash
kubectl port-forward -n catalystlab-shared svc/pgvector-cluster-rw 5432:5432
```

In a separate terminal, optionally forward the embedding model (or use external endpoint):

```bash
kubectl port-forward -n kserve-lab svc/qwen3-embedding-8b-kserve-workload-svc 8000:8000
```

#### 2. Configure connection settings

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your settings:

```yaml
# Database connection (via port-forward)
database:
  host: localhost
  port: 5432
  database: vectordb
  user: vectordb
  password: <PLACEHOLDER>  # Get from: kubectl get secret pgvector-cluster-app -n catalystlab-shared -o jsonpath='{.data.password}' | base64 -d

# Embedding model endpoint
embedding:
  # Option 1: Via port-forward
  url: http://localhost:8000/v1/embeddings

  # Option 2: External cluster endpoint
  # url: http://<CLUSTER_IP>/kserve-lab/qwen3-embedding-8b/v1/embeddings

  model: Qwen/Qwen3-Embedding-8B
  dimensions: 4096

# UMAP parameters for dimensionality reduction
umap:
  n_neighbors: 30      # Higher for 4096d embeddings
  min_dist: 0.1
  metric: cosine

# KNN graph for connections
knn:
  k: 5                 # Connect each node to 5 nearest neighbors

# Server settings
server:
  host: 0.0.0.0
  port: 8000
```

#### 3. Get database password

```bash
kubectl get secret pgvector-cluster-app -n catalystlab-shared \
  -o jsonpath='{.data.password}' | base64 -d && echo
```

Update `config.yaml` with this password.

#### 4. Build the cortex

This fetches vectors from pgvector and generates the 3D visualization data:

```bash
uv run python ingest.py
```

Expected output:

```
🔗 Connecting to pgvector...
✓ Connected to vectordb
📊 Found 152 vectors in database
🧮 Applying UMAP (4096d → 3d)...
✓ UMAP complete
🔗 Building KNN graph (k=5)...
✓ KNN graph built (760 connections)
💾 Saving to golem_cortex.json...
✓ Cortex saved (152 nodes, 760 edges)
🧠 Golem cortex is ready!
```

This creates `golem_cortex.json` with 3D positions for all vectors.

#### 5. Start the visualization server

```bash
uv run python GolemServer.py
```

Expected output:

```
🧠 Starting Golem Neural Memory Visualizer...
✓ Loaded cortex: 152 nodes, 760 edges
✓ Embedding endpoint: http://localhost:8000/v1/embeddings
🌐 Server running at http://localhost:8000
```

#### 6. Open the visualization

Navigate to: **http://localhost:8000**

### Option 2: Cluster Deployment

For production deployment inside the cluster, see [deployment.yaml](deployment.yaml).

```bash
# Create namespace (if deploying separately)
kubectl create namespace project-golem

# Create secret for database credentials
kubectl create secret generic golem-db-secret -n project-golem \
  --from-literal=password=<PGVECTOR_PASSWORD>

# Deploy
kubectl apply -f deployment.yaml
```

## Usage

### Controls

| Action | Control |
|--------|---------|
| **Rotate Camera** | Left Click + Drag |
| **Pan Camera** | Right Click + Drag |
| **Zoom** | Scroll |
| **Search Memory** | Type in search bar + Enter |

### Querying the Memory

1. Type a query in the search bar (e.g., "quantum computing")
2. Press Enter
3. The system will:
   - Generate a 4096d embedding via Qwen3-Embedding-8B
   - Search pgvector for similar vectors
   - Highlight matching nodes in the 3D space
   - Pulse/glow effect on top matches

### Understanding the Visualization

- **Nodes (Spheres)**: Each node represents a chunk of text from your knowledge base
- **Colors**: Different colors represent different categories or distance clusters
- **Connections (Lines)**: KNN edges showing semantic relationships
- **Size**: Can be weighted by importance, recency, or other metadata
- **Glow/Highlight**: Active during queries to show relevant memories

## Data Ingestion Methods

Project Golem supports multiple data ingestion strategies for populating the vector database with diverse content. Each method serves different use cases and data volumes.

### Overview of Ingestion Approaches

| Method | Script | Documents | Approach | Use Case |
|--------|--------|-----------|----------|----------|
| **Bulk Upload** | `bulk_upload.py` | ~10 sample docs | Via LLaMA Stack API | Quick testing with curated content |
| **Wikipedia Batch** | `wikipedia_ingest.py` | 200+ articles | Via LLaMA Stack API | Comprehensive knowledge base from Wikipedia |
| **Direct Small** | `direct_ingest.py` | 28 documents | Direct pgvector insertion | Bypasses LLaMA Stack for full control |
| **Direct Expanded** | `direct_ingest_expanded.py` | 180 documents | Direct pgvector insertion | Dense visualization with 20 categories |

### Method 1: Bulk Upload (LLaMA Stack)

**File:** `bulk_upload.py`

Uploads pre-written technical documents through LLaMA Stack's document ingestion API. LLaMA Stack handles chunking, embedding generation, and storage.

**Sample topics:**
- AI Transformers
- Quantum Computing Basics
- Neural Plasticity
- Blockchain Consensus
- Renaissance Humanism

**Usage:**

```bash
# Local execution
uv run python bulk_upload.py

# Kubernetes Job
kubectl apply -f bulk-upload-job.yaml
kubectl logs -f job/golem-bulk-upload -n catalystlab-shared
```

**Expected output:**

```
📤 Uploading 10 documents to LLaMA Stack...
✓ Uploaded: ai_transformers.txt
✓ Uploaded: quantum_computing_basics.txt
...
✅ Bulk upload complete: 10/10 documents
```

**Advantages:**
- Leverages LLaMA Stack's chunking logic
- Automatic embedding generation
- Metadata tracking via LLaMA Stack

**Limitations:**
- Dependent on LLaMA Stack service availability
- Less control over chunking boundaries
- No category metadata (yet)

### Method 2: Wikipedia Batch Ingestion (LLaMA Stack)

**File:** `wikipedia_ingest.py`

Fetches 200+ Wikipedia articles across 13 topic categories and ingests them via LLaMA Stack. Provides comprehensive, encyclopedic knowledge base for the neural memory visualization.

**Categories (200+ total articles):**
- AI & Machine Learning (21 articles)
- Robotics & Automation (15 articles)
- Quantum & Physics (19 articles)
- Neuroscience & Cognition (17 articles)
- Space & Astronomy (18 articles)
- Cryptography & Security (15 articles)
- Renaissance & Art (14 articles)
- Biology & Genetics (19 articles)
- Computer Science (18 articles)
- Mathematics (18 articles)
- Philosophy & Logic (16 articles)
- History (15 articles)
- Economics & Finance (13 articles)

**Usage:**

```bash
# Local execution
uv run python wikipedia_ingest.py

# Kubernetes Job
kubectl apply -f wikipedia-ingest-job.yaml
kubectl logs -f job/golem-wikipedia-ingest -n catalystlab-shared
```

**Expected output:**

```
📚 Wikipedia Batch Ingestion Starting...
Category: AI & Machine Learning (21 articles)
  ✓ Fetched: Artificial_intelligence
  ✓ Fetched: Machine_learning
  ...
✅ Ingestion complete: 218 articles across 13 categories
⏱  Total time: 45 minutes
```

**Advantages:**
- Rich, authoritative content from Wikipedia
- Organized by category for semantic clustering
- Large dataset (200+ documents) for dense visualization
- Real-world knowledge representation

**Limitations:**
- Long ingestion time (45+ minutes for 200 articles)
- Requires stable network connection to Wikipedia API
- Depends on LLaMA Stack availability

### Method 3: Direct pgvector Ingestion (Small Dataset)

**File:** `direct_ingest.py`

Bypasses LLaMA Stack entirely, generating embeddings via Qwen3-Embedding-8B and inserting directly into pgvector. Provides full control over chunking, metadata, and categories.

**Dataset:** 28 hand-crafted documents across 10 categories
- 2-3 documents per category (AI, Quantum, Neuroscience, Crypto, Art, Biology, CS, Math, Robotics, Space)

**Usage:**

```bash
# Local execution
uv run python direct_ingest.py

# Kubernetes Job
kubectl apply -f direct-ingest-job.yaml
kubectl logs -f job/golem-direct-ingest -n catalystlab-shared
```

**Expected output:**

```
🔗 Connecting to pgvector (vectordb database)...
✓ Connected
📝 Preparing 28 documents...
🧮 Generating embeddings via Qwen3-Embedding-8B...
  ✓ Batch 1/4: 10 embeddings
  ✓ Batch 2/4: 10 embeddings
  ...
💾 Inserting into pgvector...
✅ Direct ingestion complete: 28 documents
```

**Advantages:**
- Full control over document content, chunking, and metadata
- No dependency on LLaMA Stack service
- Category metadata included for visualization coloring
- Fast ingestion (minutes vs. hours)
- Predictable, curated dataset

**Limitations:**
- Manual document curation required
- Must handle embedding generation directly
- Smaller dataset (28 docs)

### Method 4: Direct pgvector Ingestion (Expanded Dataset)

**File:** `direct_ingest_expanded.py`

Extended version of direct ingestion with **180 documents across 20 categories** (9 per category). Creates a denser neural memory graph for more compelling visualization.

**Categories (180 total documents):**
- AI & Machine Learning (9)
- Quantum & Physics (9)
- Neuroscience & Cognition (9)
- Cryptography & Security (9)
- Renaissance & Art (9)
- Biology & Genetics (9)
- Computer Science (9)
- Mathematics (9)
- Robotics & Automation (9)
- Space & Astronomy (9)
- Philosophy & Logic (9)
- History (9)
- Economics & Finance (9)
- Materials Science (9)
- Climate Science (9)
- Psychology (9)
- Linguistics (9)
- Energy Systems (9)
- Urban Planning (9)
- Literature (9)

**Usage:**

```bash
# Local execution
uv run python direct_ingest_expanded.py

# Kubernetes Job
kubectl apply -f direct-ingest-expanded-job.yaml
kubectl logs -f job/golem-direct-ingest-expanded -n catalystlab-shared
```

**Expected output:**

```
🔗 Connecting to pgvector (vectordb database)...
✓ Connected
📝 Preparing 180 documents across 20 categories...
🧮 Generating embeddings via Qwen3-Embedding-8B...
  ✓ Batch 1/18: 10 embeddings
  ...
  ✓ Batch 18/18: 10 embeddings
💾 Inserting into pgvector...
✅ Direct ingestion complete: 180 documents
⏱  Total time: 8 minutes
```

**Advantages:**
- Dense visualization with 180 nodes (900+ KNN edges at k=5)
- 20 distinct categories for rich semantic structure
- Balanced distribution (9 docs per category)
- Full metadata control
- Faster than Wikipedia ingestion

**Limitations:**
- Manually curated content (vs. Wikipedia's depth)
- Larger embedding batch size requires more memory

### Cortex Regeneration After Ingestion

After adding new data via any ingestion method, regenerate the 3D cortex visualization:

**Local:**

```bash
uv run python ingest.py
```

**Kubernetes Job:**

```bash
kubectl apply -f cortex-regenerate-job.yaml
kubectl logs -f job/golem-cortex-regenerate -n catalystlab-shared
```

**Expected output:**

```
🔗 Connecting to pgvector...
✓ Connected to vectordb
📊 Found 180 vectors in database
🧮 Applying UMAP (4096d → 3d)...
✓ UMAP complete
🔗 Building KNN graph (k=5)...
✓ KNN graph built (900 connections)
💾 Saving to golem_cortex.json...
✓ Cortex saved (180 nodes, 900 edges)
🧠 Golem cortex is ready!
```

This creates/updates `golem_cortex.json` with 3D positions for all vectors. Restart `GolemServer.py` to reload the visualization.

### Choosing the Right Ingestion Method

**Use Bulk Upload when:**
- Testing the system with minimal setup
- You have specific curated documents to add
- You want LLaMA Stack's automatic chunking

**Use Wikipedia Batch when:**
- Building a comprehensive knowledge base
- You need authoritative, real-world content
- You want diverse topics for semantic clustering
- Time for 45+ minute ingestion is acceptable

**Use Direct Ingestion (Small) when:**
- You need full control over content and metadata
- You want fast, predictable ingestion
- LLaMA Stack is unavailable
- You're testing visualization with specific data

**Use Direct Ingestion (Expanded) when:**
- You need dense visualization (180+ nodes)
- You want balanced category distribution
- You need full control but want substantial data volume
- You're demoing the system and want impressive visuals

### Additional Ingestion Scripts

**Backup/Experimental Scripts (not for production):**

- `direct_ingest_28docs_backup.py` - Backup of original 28-doc version
- `direct_ingest_360.py` - Experimental 360-document variant (development)

These are kept for reference but not actively maintained.

## Configuration

### UMAP Parameters

UMAP (Uniform Manifold Approximation and Projection) reduces 4096 dimensions to 3. Key parameters:

| Parameter | Default | Range | Effect |
|-----------|:-------:|:-----:|--------|
| `n_neighbors` | 30 | 5-100 | Local vs global structure. Higher = more global structure preservation. Increased from 15 (typical) due to 4096d. |
| `min_dist` | 0.1 | 0.0-1.0 | Tightness of clusters. Lower = tighter clusters. |
| `metric` | cosine | various | Distance metric. Cosine is standard for embeddings. |

For 4096-dimension embeddings, `n_neighbors=30` is recommended (vs. 15 for lower dims).

### KNN Graph

The visualization connects each node to its `k` nearest neighbors to show semantic relationships:

| Parameter | Default | Effect |
|-----------|:-------:|--------|
| `k` | 5 | Number of connections per node. Higher = denser graph. |

Adjust in `config.yaml` under `knn.k`.

### Database Query Customization

By default, `ingest.py` fetches all vectors from the `vectors` table. To filter or customize:

Edit `ingest.py` around line 50:

```python
# Fetch all vectors
cursor.execute("SELECT id, content, embedding FROM vectors")

# Or filter by category/metadata
cursor.execute("""
    SELECT id, content, embedding, metadata
    FROM vectors
    WHERE metadata->>'category' = 'documentation'
    LIMIT 1000
""")
```

### Vector Refresh

When new documents are added to LLaMA Stack:

1. Re-run `ingest.py` to regenerate `golem_cortex.json`
2. Restart `GolemServer.py` to reload the visualization

For live updates, consider adding a refresh endpoint or file watching.

## Verification

### Check cortex file was created

```bash
ls -lh golem_cortex.json
```

Expected: JSON file with size proportional to number of vectors.

### Inspect cortex structure

```bash
uv run python -c "
import json
with open('golem_cortex.json') as f:
    cortex = json.load(f)
print(f'Nodes: {len(cortex[\"nodes\"])}')
print(f'Edges: {len(cortex[\"edges\"])}')
print(f'Sample node: {cortex[\"nodes\"][0]}')
"
```

Expected output:

```
Nodes: 152
Edges: 760
Sample node: {'id': 'vec_123', 'content': 'Sample text...', 'position': [0.45, -0.23, 1.12], 'category': 'default'}
```

### Test embedding endpoint

```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "test query", "model": "Qwen/Qwen3-Embedding-8B"}' \
  | jq '.data[0].embedding | length'
```

Expected: `4096`

### Test query endpoint

```bash
curl http://localhost:8000/query?q=quantum+computing | jq '.results | length'
```

Expected: Array of matching vectors with similarity scores.

## Caveats

### pgvector Dimension Limits

pgvector 0.8.0 has a 2,000-dimension limit for ANN indexes (HNSW/IVFFlat). Our 4096-dimension Qwen3-Embedding-8B vectors **use sequential scan** for similarity search. This is acceptable for demo-scale data (<10K vectors) but would need optimization for production:

- **Option 1**: Use Matryoshka dimension reduction (requires vLLM fix)
- **Option 2**: Truncate to 4000 dims and use `halfvec` type
- **Option 3**: Switch to a lower-dimensional embedding model

See [pgvector/README.md](../pgvector/README.md) for details.

### UMAP Non-Determinism

UMAP includes random initialization. For reproducible visualizations, set a random seed in `ingest.py`:

```python
reducer = umap.UMAP(n_components=3, n_neighbors=30, min_dist=0.1, random_state=42)
```

Without this, node positions will change slightly on each run (but semantic relationships remain consistent).

### Data Freshness

The visualization is a snapshot of pgvector at the time `ingest.py` was run. New documents added to LLaMA Stack will not appear until you regenerate `golem_cortex.json`.

For live visualization, consider:
- Adding a `/refresh` endpoint that re-runs UMAP
- File watching to detect new vectors
- Incremental UMAP updates (experimental)

### Browser Performance

Three.js rendering performance depends on:
- **Number of nodes**: 10K+ nodes may require Level-of-Detail (LOD) optimization
- **Number of edges**: KNN graph with k=5 creates manageable edge count
- **GPU**: WebGL acceleration required for smooth interaction

For large datasets (>10K vectors), consider:
- Clustering similar nodes
- Rendering only visible nodes (frustum culling)
- Using instanced meshes for better performance

### Cluster Network Access

When running locally with port-forwarding:
- Port-forward sessions can timeout after inactivity
- Embedding requests will fail if port-forward drops
- Workaround: Use external cluster endpoint in `config.yaml`

External endpoint (no port-forward needed):
```yaml
embedding:
  url: http://<CLUSTER_IP>/kserve-lab/qwen3-embedding-8b/v1/embeddings
```

Replace `<CLUSTER_IP>` with your cluster's external IP (available via `kubectl get svc` or documentation).

### Security Considerations

- **Never commit `config.yaml`** with real passwords — it's in `.gitignore`
- Use `secretKeyRef` in Kubernetes deployments (see `deployment.yaml`)
- The Flask server has no authentication — do not expose publicly without adding auth
- External embedding endpoint is unauthenticated — ensure cluster network policies are configured

## Customization

### Changing Visual Style

Edit `app/static/golem.js`:

```javascript
// Node appearance
const nodeGeometry = new THREE.SphereGeometry(0.05, 16, 16);
const nodeMaterial = new THREE.MeshStandardMaterial({
    color: categoryColors[node.category] || 0x00ff00,
    emissive: 0x00ff00,
    emissiveIntensity: 0.3
});

// Edge appearance
const edgeMaterial = new THREE.LineBasicMaterial({
    color: 0x444444,
    opacity: 0.3,
    transparent: true
});
```

### Adding Metadata Overlays

To display metadata (timestamps, categories, importance scores):

1. Include metadata in `ingest.py`:
   ```python
   cursor.execute("SELECT id, content, embedding, metadata FROM vectors")
   ```

2. Add to cortex JSON:
   ```python
   nodes.append({
       'id': vec_id,
       'content': content,
       'position': pos.tolist(),
       'metadata': metadata  # New
   })
   ```

3. Render in `golem.js`:
   ```javascript
   // Show metadata on hover
   node.userData.metadata = nodeData.metadata;
   ```

### Integrating with LLaMA Stack API

For deeper integration with LLaMA Stack:

```python
# Query LLaMA Stack memory API
import requests
response = requests.post(
    "http://llamastack-service.catalystlab-shared.svc:8321/memory/documents/query",
    json={"query": "user query", "top_k": 10}
)
# Map results to Golem visualization
```

## Troubleshooting

### "No vectors found in database"

**Cause**: pgvector `vectors` table is empty or doesn't exist.

**Solution**:
1. Verify LLaMA Stack has ingested documents:
   ```bash
   kubectl exec -n catalystlab-shared pgvector-cluster-1 -- \
     psql -U vectordb -d vectordb -c "SELECT COUNT(*) FROM vectors;"
   ```
2. If empty, use LLaMA Stack API to ingest documents first.
3. Check table name — adjust query in `ingest.py` if LLaMA Stack uses a different table name.

### "UMAP fitting failed"

**Cause**: Not enough data points or invalid vectors.

**Solution**:
- UMAP requires `n_neighbors < n_samples`. If you have <30 vectors, reduce `umap.n_neighbors` in config.
- Check for NaN/inf in embeddings:
  ```sql
  SELECT COUNT(*) FROM vectors WHERE embedding IS NULL;
  ```

### "Connection refused to embedding endpoint"

**Cause**: Port-forward dropped or service is down.

**Solution**:
1. Check port-forward is still active:
   ```bash
   ps aux | grep port-forward
   ```
2. Restart port-forward if needed.
3. Or use external endpoint in `config.yaml`.
4. Verify embedding service is running:
   ```bash
   kubectl get pods -n kserve-lab | grep qwen3-embedding
   ```

### "Three.js blank screen"

**Cause**: Browser WebGL not enabled or JavaScript errors.

**Solution**:
1. Open browser DevTools Console (F12) and check for errors
2. Verify WebGL is supported: visit https://get.webgl.org/
3. Check `golem_cortex.json` is being served:
   ```bash
   curl http://localhost:8000/cortex
   ```
4. Inspect network tab for failed requests

### "Nodes are too clustered / too spread out"

**Cause**: UMAP parameters need tuning for your dataset.

**Solution**:
- **Too clustered**: Increase `umap.min_dist` (try 0.3-0.5)
- **Too spread out**: Decrease `umap.min_dist` (try 0.01-0.05)
- **No clear structure**: Adjust `umap.n_neighbors`:
  - Lower (10-20) = local structure
  - Higher (30-50) = global structure

Re-run `ingest.py` after changing `config.yaml`.

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                        AI Catalyst Lab Cluster                      │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│  catalystlab-shared namespace:                                     │
│  ┌────────────────────┐                                            │
│  │  pgvector          │                                            │
│  │  (vectordb DB)     │◄────── LLaMA Stack ingests docs           │
│  │  - 4096d vectors   │                                            │
│  │  - Sequential scan │                                            │
│  └──────┬─────────────┘                                            │
│         │                                                           │
│         │ Port-forward (5432)                                       │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────┐                   │
│  │         Local Development Machine            │                   │
│  ├─────────────────────────────────────────────┤                   │
│  │  ingest.py:                                  │                   │
│  │  1. Fetch all vectors from pgvector         │                   │
│  │  2. UMAP: 4096d → 3d                         │                   │
│  │  3. Build KNN graph                          │                   │
│  │  4. Save golem_cortex.json                   │                   │
│  │                                               │                   │
│  │  GolemServer.py (Flask):                     │                   │
│  │  - Serve Three.js frontend                   │                   │
│  │  - Handle /query endpoint                    │                   │
│  │  - Call Qwen3-Embedding-8B for queries       │                   │
│  │  - Search pgvector for matches               │                   │
│  └─────────────────────────────────────────────┘                   │
│         ↑                                                           │
│         │ Port-forward (8000)                                       │
│         │                                                           │
│  kserve-lab namespace:                                             │
│  ┌────────────────────┐                                            │
│  │ Qwen3-Embedding-8B │                                            │
│  │ (vLLM)             │                                            │
│  │ - 4096 dimensions  │                                            │
│  │ - /v1/embeddings   │                                            │
│  └────────────────────┘                                            │
│                                                                     │
└───────────────────────────────────────────────────────────────────┘
```

## References

- [Original Project Golem](https://github.com/JayDi11a/Project_Golem) — Wikipedia-based demo
- [Project Golem Milvus](https://github.com/JayDi11a/Project_Golem_Milvus) — Milvus + OpenAI variant
- [UMAP Documentation](https://umap-learn.readthedocs.io/) — Dimensionality reduction
- [Three.js](https://threejs.org/) — 3D WebGL library
- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension
- [LLaMA Stack](../llamastack/README.md) — RAG pipeline integration

## Future Enhancements

- **Live refresh**: Auto-update visualization when new vectors are added
- **Temporal view**: Animate how the memory space evolves over time
- **Cluster highlighting**: Color nodes by topic clusters (via k-means on embeddings)
- **Metadata filters**: Filter visible nodes by category, date, importance
- **Graph analytics**: Show centrality, communities, semantic neighborhoods
- **Agent trace overlay**: Visualize which memories an agent accessed during a conversation
- **Comparison mode**: Show before/after when RAG system is retrained

---

**Status**: Experimental — visualization tool for understanding RAG memory structures in the catalyst-lab environment.
