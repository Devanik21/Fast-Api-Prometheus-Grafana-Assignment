# FastAPI Monitoring with Prometheus, Grafana, Loki, and Jaeger

This project demonstrates a FastAPI application with comprehensive monitoring using:
- **Prometheus** for metrics collection
- **Grafana** for visualization
- **Loki** for log aggregation
- **Jaeger** for distributed tracing

## Prerequisites

- Docker and Docker Compose installed on your system
- Python 3.8+ (for running the load test)

## Project Structure

```
fastapi-monitoring-assignment/
├── app/                    # FastAPI application
│   ├── Dockerfile          # Dockerfile for the FastAPI app
│   ├── requirements.txt    # Python dependencies
│   └── main.py            # FastAPI application code
├── prometheus/            
│   └── prometheus.yml     # Prometheus configuration
├── grafana/
│   └── provisioning/
│       └── datasources/   # Grafana data sources
│           └── datasource.yml
├── promtail/
│   └── promtail-config.yml # Promtail configuration for log shipping
├── docker-compose.yml     # Docker Compose configuration
├── load_test.py           # Script to generate traffic
└── README.md             # This file
```

## Getting Started

1. **Start the services**
   ```bash
   docker-compose up -d
   ```

2. **Access the services**:
   - FastAPI Application: http://localhost:8000
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)
   - Jaeger UI: http://localhost:16686

3. **Generate traffic** (optional):
   ```bash
   python load_test.py
   ```
   This will simulate traffic to the FastAPI endpoints.

## Setting up Grafana Dashboards

1. Log in to Grafana at http://localhost:3000 (admin/admin)
2. Import the following dashboards:
   - **FastAPI Monitoring**: Use ID `13639`
   - **Loki Logs**: Use ID `13639`
   - **Jaeger**: Use the built-in Jaeger data source

## Endpoints

- `GET /` - Welcome endpoint
- `GET /api/data` - Sample API endpoint that returns some data
- `GET /metrics` - Prometheus metrics endpoint

## Viewing Traces

Traces can be viewed in the Jaeger UI at http://localhost:16686. Select the `fastapi-monitoring-demo` service to view traces.

## Stopping the Services

To stop all services:
```bash
docker-compose down
```

To stop and remove all data volumes:
```bash
docker-compose down -v
```

## License

This project is licensed under the MIT License.
