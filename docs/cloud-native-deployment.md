# 云原生部署架构 - 可扩展性设计

## 部署策略：从单机到分布式

### 阶段1：单机部署 (MVP快速验证)
```yaml
# docker-compose.yml - 单机版本
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/lg_platform
      - REDIS_URL=redis://redis:6378/0
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: lg_platform
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HTTP_PORT=8000

volumes:
  postgres_data:
  redis_data:
  chroma_data:
```

### 阶段2：Kubernetes部署 (生产就绪)

#### Namespace和基础配置
```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lg-platform

---
# k8s/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lg-platform-config
  namespace: lg-platform
data:
  LOG_LEVEL: "INFO"
  CHROMA_HOST: "chroma-service"
  CHROMA_PORT: "8000"
  REDIS_URL: "redis://redis-service:6378/0"
```

#### 后端服务部署
```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lg-platform-backend
  namespace: lg-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: lg-platform-backend
  template:
    metadata:
      labels:
        app: lg-platform-backend
    spec:
      containers:
      - name: backend
        image: lg-platform/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        envFrom:
        - configMapRef:
            name: lg-platform-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        # 优雅关闭
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]

---
apiVersion: v1
kind: Service
metadata:
  name: lg-platform-backend
  namespace: lg-platform
spec:
  selector:
    app: lg-platform-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 前端服务部署
```yaml
# k8s/base/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lg-platform-frontend
  namespace: lg-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: lg-platform-frontend
  template:
    metadata:
      labels:
        app: lg-platform-frontend
    spec:
      containers:
      - name: frontend
        image: lg-platform/frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"

---
apiVersion: v1
kind: Service
metadata:
  name: lg-platform-frontend
  namespace: lg-platform
spec:
  selector:
    app: lg-platform-frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

### 自动扩缩容配置

#### HPA (Horizontal Pod Autoscaler)
```yaml
# k8s/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lg-platform-backend-hpa
  namespace: lg-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lg-platform-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  # 自定义指标扩缩容
  - type: Pods
    pods:
      metric:
        name: active_agents_per_pod
      target:
        type: AverageValue
        averageValue: "5"

---
# 前端HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lg-platform-frontend-hpa
  namespace: lg-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lg-platform-frontend
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

#### VPA (Vertical Pod Autoscaler)
```yaml
# k8s/base/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: lg-platform-backend-vpa
  namespace: lg-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lg-platform-backend
  updatePolicy:
    updateMode: "Auto"  # 或 "Off" 仅推荐不自动更新
  resourcePolicy:
    containerPolicies:
    - containerName: backend
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2
        memory: 2Gi
      mode: Auto
```

### 数据库高可用

#### PostgreSQL with Operator
```yaml
# k8s/base/postgres-cluster.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: lg-platform-postgres
  namespace: lg-platform
spec:
  instances: 3

  postgresql:
    parameters:
      max_connections: "200"
      shared_preload_libraries: "pg_stat_statements"

  bootstrap:
    initdb:
      database: lg_platform
      owner: lg_user
      secret:
        name: postgres-credentials

  storage:
    size: 100Gi
    storageClass: ssd

  # 自动备份
  backup:
    retentionPolicy: "30d"
    barmanObjectStore:
      s3Credentials:
        accessKeyId:
          name: backup-credentials
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: backup-credentials
          key: SECRET_ACCESS_KEY
      wal:
        retention: "5d"
      data:
        retention: "30d"

  # 监控
  monitoring:
    enabled: true

---
# 读写分离服务
apiVersion: v1
kind: Service
metadata:
  name: lg-platform-postgres-rw  # 读写服务
  namespace: lg-platform
spec:
  selector:
    cnpg.io/cluster: lg-platform-postgres
    role: primary
  ports:
  - port: 5432

---
apiVersion: v1
kind: Service
metadata:
  name: lg-platform-postgres-ro  # 只读服务
  namespace: lg-platform
spec:
  selector:
    cnpg.io/cluster: lg-platform-postgres
  ports:
  - port: 5432
```

#### Redis Cluster
```yaml
# k8s/base/redis-cluster.yaml
apiVersion: redis.redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: lg-platform-redis
  namespace: lg-platform
spec:
  clusterSize: 3
  clusterVersion: v7.0.5

  redisExporter:
    enabled: true
    image: quay.io/opstree/redis-exporter:1.45.0

  storage:
    nodeSelector:
      node-type: redis
    volumeClaimTemplate:
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
        storageClassName: ssd

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

### Ingress和负载均衡

#### Traefik配置
```yaml
# k8s/base/traefik-ingress.yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: lg-platform-web
  namespace: lg-platform
spec:
  entryPoints:
  - websecure
  routes:
  - match: Host(`lg-platform.example.com`)
    kind: Rule
    services:
    - name: lg-platform-frontend
      port: 80
  - match: Host(`lg-platform.example.com`) && PathPrefix(`/api`)
    kind: Rule
    services:
    - name: lg-platform-backend
      port: 80
    middlewares:
    - name: api-rate-limit
    - name: api-auth

  tls:
    certResolver: letsencrypt

---
# 中间件配置
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: api-rate-limit
  namespace: lg-platform
spec:
  rateLimit:
    burst: 100
    average: 50

---
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: api-auth
  namespace: lg-platform
spec:
  headers:
    customRequestHeaders:
      X-Real-IP: "%{X-Forwarded-For}"
      X-Forwarded-Proto: "https"
```

### 多环境部署 (Kustomize)

#### Base配置
```yaml
# k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- namespace.yaml
- configmap.yaml
- backend-deployment.yaml
- frontend-deployment.yaml
- postgres-cluster.yaml
- redis-cluster.yaml
- hpa.yaml
- vpa.yaml
- traefik-ingress.yaml

commonLabels:
  app.kubernetes.io/name: lg-platform
  app.kubernetes.io/version: v1.0.0
```

#### 开发环境覆盖
```yaml
# k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../../base

patches:
# 减少副本数
- target:
    kind: Deployment
    name: lg-platform-backend
  patch: |
    - op: replace
      path: /spec/replicas
      value: 1

# 降低资源限制
- target:
    kind: Deployment
    name: lg-platform-backend
  patch: |
    - op: replace
      path: /spec/template/spec/containers/0/resources/limits/memory
      value: "256Mi"

configMapGenerator:
- name: lg-platform-config
  behavior: merge
  literals:
  - LOG_LEVEL=DEBUG
  - ENVIRONMENT=development

secretGenerator:
- name: database-secret
  literals:
  - url=postgresql://dev_user:dev_pass@postgres:5432/lg_platform_dev
```

#### 生产环境覆盖
```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../../base

patches:
# 增加副本数
- target:
    kind: Deployment
    name: lg-platform-backend
  patch: |
    - op: replace
      path: /spec/replicas
      value: 5

# 生产资源配置
- target:
    kind: Deployment
    name: lg-platform-backend
  patch: |
    - op: replace
      path: /spec/template/spec/containers/0/resources
      value:
        requests:
          memory: "512Mi"
          cpu: "500m"
        limits:
          memory: "2Gi"
          cpu: "1000m"

configMapGenerator:
- name: lg-platform-config
  behavior: merge
  literals:
  - LOG_LEVEL=INFO
  - ENVIRONMENT=production

# 使用外部密钥管理
secretGenerator:
- name: database-secret
  files:
  - database-url=secrets/prod-db-url.txt
```

### 自动部署脚本

#### CI/CD Pipeline
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-dev}
NAMESPACE="lg-platform"

echo "部署到环境: $ENVIRONMENT"

# 构建镜像
docker build -t lg-platform/backend:latest ./backend
docker build -t lg-platform/frontend:latest ./frontend

# 推送到镜像仓库
docker tag lg-platform/backend:latest $REGISTRY/lg-platform/backend:$BUILD_ID
docker tag lg-platform/frontend:latest $REGISTRY/lg-platform/frontend:$BUILD_ID

docker push $REGISTRY/lg-platform/backend:$BUILD_ID
docker push $REGISTRY/lg-platform/frontend:$BUILD_ID

# 更新Kubernetes部署
cd k8s/overlays/$ENVIRONMENT

# 更新镜像标签
kustomize edit set image lg-platform/backend=$REGISTRY/lg-platform/backend:$BUILD_ID
kustomize edit set image lg-platform/frontend=$REGISTRY/lg-platform/frontend:$BUILD_ID

# 应用配置
kubectl apply -k .

# 等待部署完成
kubectl rollout status deployment/lg-platform-backend -n $NAMESPACE
kubectl rollout status deployment/lg-platform-frontend -n $NAMESPACE

echo "部署完成!"
```

#### 扩缩容脚本
```bash
#!/bin/bash
# scripts/scale.sh

COMPONENT=$1
REPLICAS=$2
NAMESPACE="lg-platform"

if [ -z "$COMPONENT" ] || [ -z "$REPLICAS" ]; then
    echo "使用方法: $0 <backend|frontend> <副本数>"
    exit 1
fi

case $COMPONENT in
    "backend")
        kubectl scale deployment lg-platform-backend --replicas=$REPLICAS -n $NAMESPACE
        ;;
    "frontend")
        kubectl scale deployment lg-platform-frontend --replicas=$REPLICAS -n $NAMESPACE
        ;;
    *)
        echo "未知组件: $COMPONENT"
        exit 1
        ;;
esac

echo "正在扩缩容 $COMPONENT 到 $REPLICAS 个副本..."
kubectl rollout status deployment/lg-platform-$COMPONENT -n $NAMESPACE
echo "扩缩容完成!"
```

### 云厂商适配

#### AWS EKS
```yaml
# k8s/cloud/aws/storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  throughput: "1000"
  iops: "3000"
allowVolumeExpansion: true

---
# AWS Load Balancer Controller
apiVersion: v1
kind: Service
metadata:
  name: lg-platform-alb
  namespace: lg-platform
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  selector:
    app: lg-platform-frontend
  ports:
  - port: 80
    targetPort: 80
```

#### Google GKE
```yaml
# k8s/cloud/gcp/storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-retain
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
reclaimPolicy: Retain
allowVolumeExpansion: true

---
# GKE Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lg-platform-gke
  namespace: lg-platform
  annotations:
    kubernetes.io/ingress.global-static-ip-name: "lg-platform-ip"
    networking.gke.io/managed-certificates: "lg-platform-ssl-cert"
spec:
  rules:
  - host: lg-platform.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: lg-platform-frontend
            port:
              number: 80
```

### 成本优化

#### Spot实例配置
```yaml
# k8s/optimization/spot-nodepool.yaml
apiVersion: v1
kind: Node
metadata:
  labels:
    node.kubernetes.io/instance-type: "spot"
  annotations:
    cluster-autoscaler.kubernetes.io/scale-down-disabled: "false"

---
# Pod优先级
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: lg-platform-low-priority
value: 100
globalDefault: false
description: "用于非关键工作负载的低优先级"

---
# 在Agent执行容器中使用Spot实例
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lg-platform-agent-workers
spec:
  template:
    spec:
      priorityClassName: lg-platform-low-priority
      nodeSelector:
        node.kubernetes.io/instance-type: "spot"
      tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

这个云原生架构设计的优势：

1. **渐进式部署**: 从Docker Compose到Kubernetes平滑过渡
2. **自动扩缩容**: CPU/内存/自定义指标多维度扩缩容
3. **高可用性**: 数据库集群、多副本部署
4. **成本优化**: Spot实例、资源限制、智能扩缩容
5. **多环境支持**: 开发/测试/生产环境隔离
6. **云厂商中立**: 支持AWS/GCP/Azure等多云部署