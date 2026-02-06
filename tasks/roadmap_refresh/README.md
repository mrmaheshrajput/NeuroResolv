# Roadmap Refresh Lambda

This Lambda task is responsible for triggering automated roadmap refreshes in the NeuroResolv system.

## Purpose
The NeuroResolv application uses "Living Roadmaps" that should evolve as users log progress. Each resolution has a `next_roadmap_refresh` date. This Lambda triggers the backend to identify all resolutions where this date has passed and re-run the AI agents to update their plans.

## Infrastructure
- **Trigger**: AWS EventBridge Rule (Scheduled)
- **Schedule**: Weekly (`cron(0 0 ? * SUN *)`)
- **Runtime**: Python 3.14+
- **Memory**: 128MB (lightweight)
- **Timeout**: 120 seconds (to allow for multiple AI generations)

## Configuration
The Lambda requires the following environment variables:
- `API_BASE_URL`: The base URL of the NeuroResolv backend (e.g., `https://neuroresolv-api.ffinity.com`)
- `API_KEY`: A valid API key for internal system access.
