# Commands

## Docker Compose

```bash
# Start the services in detached mode
docker-compose up -d

# Or to start a specific service
docker-compose up -d devsetgoMain

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Build and start (if changes to Dockerfile)
docker-compose up -d --build

# View running containers
docker-compose ps

# Remove containers and networks
docker-compose down --remove-orphans
```