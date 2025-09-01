# Deployment and Maintenance Procedures

## Environment Setup

### Development Environment
```bash
# Clone and setup
git clone <repo-url>
cd turbo_local_coder_agent
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -e .

# Configure LLM endpoints
cp .env.example .env
# Edit .env with your Ollama/LLM settings
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["python", "-m", "agent.core.orchestrator", "serve"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  turbo-coder:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_LOCAL=http://ollama:11434
      - PLANNER_MODEL=gpt-oss:20b
      - CODER_MODEL=qwen2.5-coder:latest
    volumes:
      - ./workspace:/app/workspace
      - ./knowledge.db:/app/knowledge.db
    depends_on:
      - ollama
      
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
      
volumes:
  ollama_data:
```

## Production Deployment

### Kubernetes Configuration
```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: turbo-coder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: turbo-coder
  template:
    metadata:
      labels:
        app: turbo-coder
    spec:
      containers:
      - name: turbo-coder
        image: turbo-coder:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_LOCAL
          value: "http://ollama-service:11434"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi" 
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Environment Variables
```bash
# Production .env template
TURBO_HOST=https://api.openai.com
OLLAMA_LOCAL=http://localhost:11434
PLANNER_MODEL=gpt-4-turbo
CODER_MODEL=qwen2.5-coder:latest
OLLAMA_API_KEY=your_api_key_here
MAX_STEPS=25
REQUEST_TIMEOUT_S=120
DRY_RUN=0

# Security
ALLOWED_FILE_EXTENSIONS=.py,.js,.ts,.md,.txt,.json,.yml,.yaml
BLOCKED_DIRECTORIES=/etc,/usr,/var,/boot
MAX_FILE_SIZE_MB=10

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=1
HEALTH_CHECK_INTERVAL=30
```

## Monitoring and Observability

### Health Checks
```python
# agent/monitoring/health.py
from dataclasses import dataclass
from typing import Dict, List
import httpx
import time

@dataclass
class HealthStatus:
    """System health status for monitoring."""
    status: str  # "healthy", "degraded", "unhealthy"
    components: Dict[str, str]
    uptime_seconds: int
    last_check: str

class HealthChecker:
    """Monitor system component health."""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.start_time = time.time()
    
    async def check_llm_endpoints(self) -> Dict[str, str]:
        """Check LLM endpoint availability."""
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.config.local_host}/api/tags")
                results["ollama"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            results["ollama"] = "unhealthy"
            
        return results
    
    async def check_knowledge_base(self) -> str:
        """Check RAG system availability."""
        try:
            from agent.team.rag_system import RAGSystem
            rag = RAGSystem()
            test_results = rag.search("test query", top_k=1)
            return "healthy" if test_results else "degraded"
        except Exception:
            return "unhealthy"
    
    async def get_health_status(self) -> HealthStatus:
        """Get overall system health."""
        components = await self.check_llm_endpoints()
        components["knowledge_base"] = await self.check_knowledge_base()
        
        unhealthy_count = sum(1 for status in components.values() if status == "unhealthy")
        overall_status = "unhealthy" if unhealthy_count > 0 else "healthy"
        
        return HealthStatus(
            status=overall_status,
            components=components,
            uptime_seconds=int(time.time() - self.start_time),
            last_check=time.strftime("%Y-%m-%d %H:%M:%S")
        )
```

### Logging Configuration
```python
# agent/monitoring/logging.py
import logging
import structlog
from pythonjsonlogger import jsonlogger

def setup_logging(log_level: str = "INFO"):
    """Configure structured logging for production."""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s"
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=structlog.threadlocal.wrap_dict(dict),
        cache_logger_on_first_use=True
    )

# Usage in application code
logger = structlog.get_logger()

def log_task_execution(task_id: str, agent_type: str, status: str, duration_ms: int):
    """Log task execution for monitoring."""
    logger.info(
        "task_executed",
        task_id=task_id,
        agent_type=agent_type,
        status=status,
        duration_ms=duration_ms
    )
```

### Metrics Collection
```python
# agent/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
TASK_COUNTER = Counter('turbo_coder_tasks_total', 'Total tasks processed', ['agent_type', 'status'])
TASK_DURATION = Histogram('turbo_coder_task_duration_seconds', 'Task execution time', ['agent_type'])
ACTIVE_TASKS = Gauge('turbo_coder_active_tasks', 'Currently active tasks')
LLM_TOKEN_USAGE = Counter('turbo_coder_llm_tokens_total', 'LLM token usage', ['model', 'operation'])

def record_task_metrics(agent_type: str, status: str, duration_seconds: float):
    """Record task execution metrics."""
    TASK_COUNTER.labels(agent_type=agent_type, status=status).inc()
    TASK_DURATION.labels(agent_type=agent_type).observe(duration_seconds)

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server."""
    start_http_server(port)
    logger.info("metrics_server_started", port=port)
```

## Backup and Recovery

### Database Backup
```bash
# Backup RAG knowledge database
#!/bin/bash
BACKUP_DIR="/backups/turbo-coder"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KNOWLEDGE_DB="knowledge.db"

mkdir -p $BACKUP_DIR

# Backup knowledge database
cp $KNOWLEDGE_DB "$BACKUP_DIR/knowledge_${TIMESTAMP}.db"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "knowledge_*.db" -mtime +30 -delete

echo "Backup completed: knowledge_${TIMESTAMP}.db"
```

### Configuration Backup
```bash
# Backup system configuration
tar -czf "/backups/config_${TIMESTAMP}.tar.gz" \
    .env \
    agent/core/config.py \
    docker-compose.yml \
    k8s/ \
    --exclude=*.pyc
```

## Maintenance Procedures

### Regular Maintenance Tasks
```python
# maintenance/cleanup.py
import sqlite3
import os
from datetime import datetime, timedelta

def cleanup_old_tasks(days_to_keep: int = 30):
    """Remove old task records from database."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    with sqlite3.connect("tasks.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM task_results WHERE created_at < ?",
            (cutoff_date.isoformat(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
    
    logger.info("cleanup_completed", deleted_tasks=deleted_count)

def update_knowledge_embeddings():
    """Regenerate embeddings for knowledge base documents."""
    from agent.team.rag_system import RAGSystem
    
    rag = RAGSystem()
    updated_count = rag.refresh_embeddings()
    
    logger.info("embeddings_updated", document_count=updated_count)

def health_check_and_restart():
    """Check system health and restart unhealthy components."""
    checker = HealthChecker()
    status = checker.get_health_status()
    
    if status.status == "unhealthy":
        logger.warning("system_unhealthy", components=status.components)
        # Implement restart logic as needed
```

### Automated Maintenance
```yaml
# k8s/cronjob.yml  
apiVersion: batch/v1
kind: CronJob
metadata:
  name: turbo-coder-maintenance
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: maintenance
            image: turbo-coder:latest
            command: ["python", "-m", "maintenance.cleanup"]
            env:
            - name: TASK_RETENTION_DAYS
              value: "30"
          restartPolicy: OnFailure
```

### Troubleshooting Guide
```markdown
## Common Issues

### LLM Endpoint Unavailable
- Check Ollama service status: `docker ps | grep ollama`
- Verify network connectivity: `curl http://ollama:11434/api/tags`  
- Review logs: `docker logs ollama`
- Restart if needed: `docker restart ollama`

### High Memory Usage
- Monitor with: `docker stats turbo-coder`
- Check for memory leaks in RAG system
- Restart containers if memory > 2GB
- Scale horizontally if persistent

### Task Queue Backlog
- Check active tasks: `kubectl get pods -l app=turbo-coder`
- Scale replicas: `kubectl scale deployment turbo-coder --replicas=5`
- Monitor task completion rates
- Investigate slow/stuck tasks

### Knowledge Base Corruption
- Stop application
- Restore from backup: `cp /backups/knowledge_latest.db knowledge.db`
- Rebuild embeddings: `python -m maintenance.rebuild_embeddings`
- Restart application
```