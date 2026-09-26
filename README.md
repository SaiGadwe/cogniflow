# CogniFlow

A multi-agent cognitive study companion for neurodivergent students, built with Fetch.ai's uAgent framework and ASI-1 Mini.

## What It Does

CogniFlow adapts to how your brain works. It connects your calendar, course assignments, and cognitive profile to create personalized study plans with smart scheduling.

| Agent | Role |
|---|---|
| **Director** | Classifies intent and routes queries through the agent network |
| **Insight** | Researches disability-specific study strategies using live web search |
| **Rhythm** | Builds adapted focus sessions (duration, breaks, techniques) |
| **Sync** | Finds optimal study slots based on your actual class schedule |

## How It Works

1. User sends a message (e.g., *"help me study for my AI midterm"*)
2. Director classifies intent → triggers agent chain
3. Insight researches strategies for the student's disability
4. Rhythm builds an adapted session plan
5. Sync finds open slots around existing classes
6. Response is synthesized and returned with proposed time slots

## Tech Stack

**Backend:** Python, Fetch.ai uAgents, ASI-1 Mini  
**Frontend:** React 19, Vite, Tailwind CSS  
**Integrations:** Google Calendar API, Canvas LMS, DuckDuckGo Search  
**Protocols:** Agentverse mailbox, MCP, DeltaV chat protocol  

## Getting Started

```bash
# Clone and install
git clone https://github.com/your-repo/cogniflow.git
cd cogniflow
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in: ASI1_API_KEY, DIRECTOR_SEED, INSIGHT_SEED, RHYTHM_SEED, SYNC_SEED

# Start agents
python -m agents.insight_agent.insight_agent &
python -m agents.rhythm_agent.rhythm_agent &
python -m agents.sync_agent.sync_agent &
python -m agents.director_agent.director_agent &

# Start server
python server.py

# Frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:8080](http://localhost:8080) to use the app.