# Prompt Optimizer Lambda

This Lambda function automates prompt improvement using Opik's MetaPromptOptimizer.

## Overview

The Lambda is triggered weekly (or as configured) by AWS EventBridge. It calls the backend API to:

1. Fetch traces with negative user feedback from Opik
2. Build a dataset from the feedback
3. Run MetaPromptOptimizer to improve the prompts
4. Create new prompt versions in Opik

## Data Flywheel Process

```
User gives negative feedback → Trace logged to Opik with feedback tag
                                         ↓
Lambda triggers weekly → Fetches feedback traces
                                         ↓
Builds optimization dataset → Runs MetaPromptOptimizer
                                         ↓
Creates new prompt version → Next API calls use improved prompt
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Backend API URL | `http://localhost:8000` |
| `API_KEY` | API authentication key | `dev-api-key-12345` |
| `MIN_SAMPLES` | Minimum feedback samples needed | `5` |

## AWS EventBridge Schedule

Example schedule (every Sunday at midnight UTC):

```
cron(0 0 ? * SUN *)
```

## Local Testing

```bash
cd /path/to/NeuroResolv/tasks/prompt_optimizer
python -c "import handler; print(handler.lambda_handler({}, None))"
```

## Prompts Optimized

- `GENERATE_ROADMAP_PROMPT` - Creates learning milestone roadmaps
- `GENERATE_NORTH_STAR_PROMPT` - Generates end-of-year transformation vision

## How Feedback Improves Prompts

When users provide negative feedback (thumbs down) on generated content:

1. The feedback is logged as a trace with a specific tag (e.g., `prompt:GENERATE_ROADMAP_PROMPT`)
2. This Lambda collects those traces
3. The user's feedback text becomes guidance for what the prompt should generate
4. MetaPromptOptimizer refines the prompt to better address user concerns
5. New prompt version is automatically used by the next API calls
