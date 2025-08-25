# FastAPI + Prometheus + Grafana + Loki + Jaeger — Assignment Deliverables



** files & structure**

```
fastapi-monitoring-assignment/
├─ app/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ main.py
├─ prometheus/
│  └─ prometheus.yml
├─ grafana/
│  └─ provisioning/
│     └─ datasources/
│        └─ datasource.yml
├─ promtail/
│  └─ promtail-config.yml
├─ docker-compose.yml
├─ load_test.py
└─ README.md
```

---

## Quick summary (what this does)

* A small FastAPI app (`/` and `/sleep/{ms}`) instrumented to expose Prometheus metrics at `/metrics`, emit structured logs to stdout, and produce OpenTelemetry traces sent to Jaeger.
* `docker-compose.yml` runs: the app, Prometheus, Grafana, Loki (for logs), Promtail (to ship logs), and Jaeger (for traces).
* `load_test.py` simulates traffic so you can show request count, latency histograms, logs, and at least one trace in Grafana.

---

## How to run (short)

1. Build & start everything:

```bash
docker-compose up -d --build
```

2. Start the traffic generator (locally):

```bash
python3 load_test.py
```

3. Open these UIs in your browser:

* Grafana: [http://localhost:3000](http://localhost:3000) (default `admin`/`admin`)
* Prometheus: [http://localhost:9090](http://localhost:9090)
* Jaeger: [http://localhost:16686](http://localhost:16686)

4. In Grafana you'll already have data sources configured (Prometheus, Loki, Jaeger). Use Explore / Dashboards to visualize metrics, logs, and traces.

---

## Recording checklist for the 3–5 min screen recording

* Show `docker-compose up -d --build` (or show the running containers)
* Run `python3 load_test.py` and show traffic being generated
* Open Grafana > Explore: show Prometheus query for `http_request_count_total` and a latency histogram/summary
* Show logs from Loki (use `{app="fastapi-assignment"}` or search by container label)
* Open Traces (Jaeger) inside Grafana (or open Jaeger UI) and show at least one request trace
* Briefly explain what you did (30–60s)

---

## Files (copy these into your project)

> **Note:** the actual file contents are below. Copy each file into the paths shown above.

---

### app/requirements.txt

```
fastapi==0.100.0
uvicorn[standard]==0.22.0
prometheus-client==0.16.0
opentelemetry-api==1.13.0
opentelemetry-sdk==1.13.0
opentelemetry-exporter-jaeger==1.13.0
python-json-logger==2.0.4
requests==2.31.0
```

---

### app/Dockerfile

```
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ./
ENV OTEL_SERVICE_NAME=fastapi-assignment
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### app/main.py

```python
from fastapi import FastAPI, Request
import time
import random
import logging
import json
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from prometheus_client import multiprocess
from prometheus_client import REGISTRY
from prometheus_client import exposition
from prometheus_client import start_http_server
from starlette.responses import Response
import sys

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Configure structured logging
logger = logging.getLogger("fastapi_assignment")
logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_request_count_total', 'Total HTTP requests', ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds', 'Latency of HTTP requests in seconds', ['method', 'endpoint']
)

# OpenTelemetry tracer (Jaeger exporter)
resource = Resource.create({"service.name": "fastapi-assignment"})
provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI()

@app.middleware("http")
async def prom_middleware(request: Request, call_next):
    start = time.time()
    method = request.method
    endpoint = request.url.path
    with tracer.start_as_current_span(f"HTTP {method} {endpoint}") as span:
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            logger.exception("Unhandled exception")
            raise
        finally:
            latency = time.time() - start
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
            logger.info(json.dumps({
                "path": endpoint,
                "method": method,
                "status": status,
                "latency": latency
            }))
    return response

@app.get('/')
async def root():
    with tracer.start_as_current_span("handler_root"):
        # simulate some work
        t = random.random() * 0.1
        time.sleep(t)
        return {"message": "hello from fastapi assignment"}

@app.get('/sleep/{ms}')
async def sleep_ms(ms: int):
    with tracer.start_as_current_span("handler_sleep"):
        t = max(0, ms) / 1000.0
        time.sleep(t)
        return {"slept_ms": ms}

@app.get('/metrics')
async def metrics():
    # Use the default registry
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
```

---

### prometheus/prometheus.yml

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'fastapi'
    metrics_path: /metrics
    static_configs:
      - targets: ['app:8000']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['prometheus:9090']
```

---

### promtail/promtail-config.yml

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          __path__: /var/lib/docker/containers/*/*.log
```

---

### grafana/provisioning/datasources/datasource.yml

```yaml
apiVersion: 1
providers: []

---

# Grafana datasource provisioning

apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
```

---

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: ./app
    container_name: fastapi-assignment
    ports:
      - '8000:8000'
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - '9090:9090'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    depends_on:
      - prometheus
      - loki
      - jaeger
    ports:
      - '3000:3000'
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - monitoring

  loki:
    image: grafana/loki:2.8.2
    ports:
      - '3100:3100'
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.8.2
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/log:/var/log:ro
      - ./promtail/promtail-config.yml:/etc/promtail/config.yml:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring

  jaeger:
    image: jaegertracing/all-in-one:1.49
    ports:
      - '16686:16686'
      - '6831:6831/udp'
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

---

### load\_test.py

```python
# Simple traffic generator
import requests
import time
import random

URL = 'http://localhost:8000'

for i in range(200):
    try:
        if random.random() < 0.3:
            # hit sleep endpoint with variable latency
            ms = random.choice([50, 100, 200, 500, 1000])
            r = requests.get(f'{URL}/sleep/{ms}', timeout=5)
        else:
            r = requests.get(URL, timeout=5)
        print(i, r.status_code, r.elapsed.total_seconds())
    except Exception as e:
        print('err', e)
    time.sleep(0.1)

print('done')
```

---

### README.md

```
See the Quick summary in the top of this document.

Full steps to run locally:

1. Make sure Docker & docker-compose are installed.
2. From repo root run: `docker-compose up -d --build`.
3. Wait ~15s for containers to start.
4. Run traffic: `python3 load_test.py`.
5. Open Grafana at http://localhost:3000 (admin/admin). Explore Prometheus ("Prometheus" datasource) and Loki ("Loki") and Jaeger traces (via Jaeger datasource).

Hints:
- In Grafana Explore you can run `rate(http_request_count_total[1m])` or inspect `http_request_latency_seconds_bucket` histogram metrics.
- To find logs from the app in Loki's Explore use `{job="varlogs"}` and then filter for `fastapi-assignment` or inspect messages containing `"path": "/"`.
- Jaeger UI: http://localhost:16686 — service dropdown will show `fastapi-assignment`.

Recording tips:
- Narrate what you do and why. Show the command you run, the traffic generation, and the Grafana visualizations.
- Make sure you capture at least one trace in Jaeger or Grafana traces while load_test.py is running.

Good luck! you’ve got this — record confidently and show them how you set it up end-to-end. 💖
```

---

If you want, I can also:

* Create a pre-built Grafana dashboard JSON for the metrics and add it to provisioning.
* Make the load test more robust (concurrent requests with asyncio or `locust`/`hey`).
* Provide a short script to make an mp4 screen recording automatically (depends on your OS).

Say the word and I’ll add the extras. 🌸
