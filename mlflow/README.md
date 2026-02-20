# MLflow Deployment on Kubernetes

Deploy MLflow as an LLM trace viewer and experiment tracking system in the `catalystlab-shared` namespace. This deployment uses CNPG PostgreSQL for metadata storage and integrates with OpenTelemetry for distributed trace collection from LLaMA Stack inference pipelines.

**Target cluster:** `159.253.136.11`
**Namespace:** `catalystlab-shared`

## Prerequisites

Before deploying MLflow, verify that the following components are available on your Kubernetes cluster.

### Verification Commands

Run these commands against your cluster to verify prerequisites:

```bash
# Check CNPG PostgreSQL cluster
kubectl get clusters.postgresql.cnpg.io -n catalystlab-shared

# Check pgvector-cluster pods
kubectl get pods -n catalystlab-shared -l cnpg.io/cluster=pgvector-cluster

# Verify PostgreSQL secret exists
kubectl get secret -n catalystlab-shared pgvector-cluster-app

# Check Nginx Ingress Controller
kubectl get ingressclass
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

# Check storage classes
kubectl get storageclass

# Verify LLaMA Stack deployment
kubectl get deployments -n catalystlab-shared
kubectl get pods -n catalystlab-shared
```

### Expected Results

#### 1. CNPG PostgreSQL Cluster

**Status:**
```
NAME               AGE   INSTANCES   READY   STATUS                     PRIMARY
pgvector-cluster   12h   1           1       Cluster in healthy state   pgvector-cluster-1
```

**Pod:**
```
NAME                 READY   STATUS    RESTARTS   AGE
pgvector-cluster-1   1/1     Running   0          12h
```

**Service endpoints:**
- `pgvector-cluster-rw` (read-write): Primary endpoint for MLflow
- `pgvector-cluster-ro` (read-only): Available for read operations
- `pgvector-cluster-r` (read): Available for read operations

**Existing databases:**
```bash
kubectl exec -n catalystlab-shared pgvector-cluster-1 -- psql -U postgres -c '\l'
```

Expected databases:
- `llamastack` (owner: vectordb)
- `vectordb` (owner: vectordb)
- **Note**: `mlflow` database must be created before deployment

#### 2. PostgreSQL Secret

**Secret name:** `pgvector-cluster-app`

Required keys:
- `username` ✅
- `password` ✅

Verify keys exist:
```bash
kubectl get secret -n catalystlab-shared pgvector-cluster-app \
  -o jsonpath='{.data}' | jq 'keys'
```

Expected output includes `username` and `password` among other connection details.

#### 3. Nginx Ingress Controller

**IngressClass:**
```
NAME    CONTROLLER             PARAMETERS   AGE
nginx   k8s.io/ingress-nginx   <none>       34d
```

**Controller pod:**
```
NAME                                       READY   STATUS    RESTARTS   AGE
ingress-nginx-controller-78c9c55db-zhbtr   1/1     Running   0          24d
```

**Service with external IP:**
```
NAME                       TYPE           EXTERNAL-IP      PORT(S)
ingress-nginx-controller   LoadBalancer   159.253.136.11   80:31123/TCP,443:31755/TCP
```

**External IP:** `159.253.136.11` - Used for constructing the MLflow ingress hostname.

#### 4. Storage Provisioner

**Available storage classes:**
```
NAME                   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE
local-path (default)   rancher.io/local-path   Delete          WaitForFirstConsumer
openebs-hostpath       openebs.io/local        Delete          WaitForFirstConsumer
openebs-lvmpv          local.csi.openebs.io    Delete          Immediate
```

MLflow will use the `local-path` storage class for artifact storage.

**Existing PVCs in catalystlab-shared:**
```
NAME                 STATUS   VOLUME       CAPACITY   STORAGECLASS
llamastack-pvc       Bound    pvc-bdfd...  10Gi       local-path
pgvector-cluster-1   Bound    pvc-cf32...  20Gi       local-path
```

#### 5. LLaMA Stack Deployment

**Deployment:**
```
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
llamastack   1/1     1            1           11h
```

**Pod:**
```
NAME                         READY   STATUS    RESTARTS   AGE
llamastack-9ffb4584c-scswr   1/1     Running   0          11h
```

**Service:**
```
NAME         TYPE        CLUSTER-IP      PORT(S)
llamastack   ClusterIP   10.110.77.210   8321/TCP
```

LLaMA Stack will send OpenTelemetry traces to the OTel Collector, which forwards them to MLflow's `/v1/traces` endpoint.

#### 6. OpenTelemetry Collector

**Status:** Not deployed yet (will be deployed after MLflow)

## Prerequisites Summary

| Component | Status | Details |
|-----------|--------|---------|
| CNPG PostgreSQL Cluster | ✅ Ready | `pgvector-cluster` healthy with 1/1 instances |
| PostgreSQL Secret | ✅ Ready | `pgvector-cluster-app` contains credentials |
| Nginx Ingress | ✅ Ready | External IP: `159.253.136.11` |
| Storage Provisioner | ✅ Ready | `local-path` storage class available |
| LLaMA Stack | ✅ Ready | Deployment running with service on port 8321 |
| OTel Collector | ⚪ Pending | To be deployed after MLflow |

## Pre-Deployment Action

Before deploying MLflow, create the `mlflow` database in PostgreSQL:

```bash
kubectl exec -n catalystlab-shared pgvector-cluster-1 -- \
  psql -U postgres -c "CREATE DATABASE mlflow OWNER vectordb;"
```

Verify the database was created:

```bash
kubectl exec -n catalystlab-shared pgvector-cluster-1 -- \
  psql -U postgres -c '\l' | grep mlflow
```

## Next Steps

1. Create the `mlflow` database (see above)
2. Deploy MLflow PVC for artifact storage
3. Deploy MLflow Deployment with PostgreSQL backend
4. Deploy MLflow Service (ClusterIP)
5. Deploy MLflow Ingress with nginx annotations
6. Verify MLflow is accessible via ingress
7. Create initial experiment for trace collection
8. Deploy OTel Collector with experiment ID
9. Configure LLaMA Stack to send traces (if not already configured)

## Architecture

```
LLaMA Stack ──(OTel SDK)──► OTel Collector ──(otlphttp)──► MLflow /v1/traces
  :8321                        :4317/:4318                      :5000
                                                                  │
                                          ┌───────────────────────┤
                                          ▼                       ▼
                                    PostgreSQL              PVC (artifacts)
                                   (metadata)              /mlflow/artifacts
```

**Data flow:**
1. LLaMA Stack emits OpenTelemetry spans during inference
2. OTel Collector receives spans on gRPC (4317) or HTTP (4318)
3. OTel Collector exports to MLflow's OTLP endpoint (`/v1/traces`)
4. MLflow stores trace metadata in PostgreSQL (`mlflow` database)
5. MLflow stores artifacts in PVC-backed filesystem
6. Users access traces and experiments via MLflow UI (port 5000)

## References

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [CloudNativePG Documentation](https://cloudnative-pg.io/documentation/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [LLaMA Stack](https://github.com/meta-llama/llama-stack)
