# 🐳 Docker Deployment Guide

This guide explains how to run the Job Application Tracker in Docker containers with scheduled email checking.

## Quick Start

### Prerequisites
- Docker installed (version 20.10+)
- Docker Compose installed (version 1.29+)

### 1. Basic Setup

```bash
# Clone the repository
git clone https://github.com/msle237-lees/job-application-tracker.git
cd job-application-tracker

# Build and start the containers
docker-compose up -d
```

The application will be available at http://localhost:8000

### 2. Setup Gmail Integration (Optional)

If you want automatic email checking:

```bash
# 1. Follow GMAIL_SETUP.md to get your credentials
# 2. Place the credentials file in ./secret/googleapi.json

# 3. Run initial OAuth authentication
docker-compose run --rm app python cli.py email-check --setup

# 4. Restart the email-checker service
docker-compose restart email-checker
```

## Architecture

The Docker setup consists of two services:

### 1. App Service (Port 8000)
- Runs the FastAPI backend
- Serves the built React frontend
- Handles all CRUD operations
- Exposes REST API endpoints

### 2. Email-Checker Service
- Runs in the background
- Checks emails on a schedule (default: every hour)
- Updates application statuses automatically
- Logs all activities

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///./job_tracker.db

# Email checker interval (in minutes)
EMAIL_CHECK_INTERVAL_MINUTES=60

# API host and port
API_HOST=0.0.0.0
API_PORT=8000
```

### docker-compose.yml Customization

**Change the check interval:**
```yaml
services:
  email-checker:
    environment:
      - EMAIL_CHECK_INTERVAL_MINUTES=30  # Check every 30 minutes
```

**Use a different port:**
```yaml
services:
  app:
    ports:
      - "3000:8000"  # Access on port 3000
```

**Add more resources:**
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

## Docker Commands

### Start Services
```bash
# Start in background
docker-compose up -d

# Start with logs visible
docker-compose up

# Start only specific service
docker-compose up -d app
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f email-checker

# Last 100 lines
docker-compose logs --tail=100 app
```

### Rebuild After Changes
```bash
# Rebuild images
docker-compose build

# Rebuild and restart
docker-compose up -d --build
```

### Access Container Shell
```bash
# App container
docker-compose exec app bash

# Email checker container
docker-compose exec email-checker bash
```

## Data Persistence

Data is persisted using Docker volumes:

- `./job_tracker.db` - SQLite database
- `./secret/` - OAuth credentials
- `./logs/` - Application logs
- `./email_config.json` - Email checker configuration

These are mounted as volumes and will persist across container restarts.

## Production Deployment

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml tracker

# Check services
docker service ls

# View logs
docker service logs -f tracker_app
```

### Using Kubernetes

See `k8s/` directory for Kubernetes manifests (to be added).

### Security Recommendations

1. **Use secrets for sensitive data:**
```yaml
services:
  app:
    secrets:
      - gmail_credentials
secrets:
  gmail_credentials:
    file: ./secret/googleapi.json
```

2. **Run as non-root user:**
```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

3. **Use environment variables for configuration**
4. **Enable HTTPS with reverse proxy (nginx/traefik)**
5. **Regularly update base images**

## Monitoring

### Health Checks

Add health checks to docker-compose.yml:

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Logging

View email checker activity:
```bash
# In container
docker-compose exec email-checker tail -f /app/logs/email_scheduler.log

# From host (if logs directory is mounted)
tail -f ./logs/email_scheduler.log
```

## Troubleshooting

### Port Already in Use
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Use 8080 instead
```

### Database Locked
```bash
# Stop all services
docker-compose down

# Remove database lock
rm job_tracker.db-journal

# Restart
docker-compose up -d
```

### Email Checker Not Working
```bash
# Check logs
docker-compose logs email-checker

# Verify credentials exist
docker-compose exec email-checker ls -la /app/secret/

# Re-run OAuth setup
docker-compose run --rm app python cli.py email-check --setup
```

### Container Won't Start
```bash
# View detailed logs
docker-compose logs app

# Check container status
docker-compose ps

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Frontend Not Loading
The frontend is built during the Docker build process. If you make changes:
```bash
# Rebuild the image
docker-compose build app

# Restart
docker-compose up -d app
```

## Development with Docker

### Hot Reload for Backend
```yaml
services:
  app:
    volumes:
      - .:/app
    command: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Hot Reload for Frontend
For development, run frontend separately:
```bash
# Start only backend in Docker
docker-compose up -d app

# Run frontend locally
cd dashboard
npm run dev
```

## Backup and Restore

### Backup
```bash
# Backup database
docker-compose exec app sqlite3 job_tracker.db ".backup '/app/backup.db'"
docker cp $(docker-compose ps -q app):/app/backup.db ./backup.db

# Or backup the volume
tar -czf backup.tar.gz job_tracker.db secret/ logs/
```

### Restore
```bash
# Restore database
docker cp ./backup.db $(docker-compose ps -q app):/app/job_tracker.db
docker-compose restart app email-checker
```

## Advanced Configuration

### Using PostgreSQL Instead of SQLite

1. Update docker-compose.yml:
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: tracker
      POSTGRES_USER: tracker
      POSTGRES_PASSWORD: secretpassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  app:
    environment:
      - DATABASE_URL=postgresql://tracker:secretpassword@db:5432/tracker
    depends_on:
      - db

volumes:
  postgres_data:
```

2. Update requirements.txt:
```
psycopg2-binary>=2.9.0
```

### Email Checking on Specific Schedule (Cron-like)

For more complex schedules, use a cron container:

```yaml
services:
  cron:
    build: .
    volumes:
      - ./job_tracker.db:/app/job_tracker.db
      - ./secret:/app/secret
    command: |
      bash -c "
        echo '0 9,17 * * * cd /app && python -c \"from email_checker import run_check; run_check()\"' | crontab -
        crond -f
      "
```

## Example Production Setup

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - app

  app:
    build: .
    expose:
      - "8000"
    environment:
      - DATABASE_URL=sqlite:///./job_tracker.db
    volumes:
      - app_data:/app/data
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  email-checker:
    build: .
    environment:
      - EMAIL_CHECK_INTERVAL_MINUTES=60
    volumes:
      - app_data:/app/data
    restart: always

volumes:
  app_data:
```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Review this guide
3. Open an issue on GitHub
