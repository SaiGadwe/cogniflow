# CogniFlow

> **Your neurodivergent brain deserves smarter tools**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react&logoColor=20232A)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5%2B-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Fetch.ai](https://img.shields.io/badge/Fetch.ai-uAgents%20%2B%20Agentverse-6B46C1)](https://fetch.ai/)

CogniFlow is a multi-agent AI study companion designed for neurodivergent students, including students with ADHD, dyslexia, autism, and anxiety. It coordinates specialized autonomous agents to turn cognitive preferences and study goals into practical learning strategies, sustainable focus sessions, and scheduled study plans.

> **Status:** Hackathon project. There is no live demo currently available.

## The problem

Most study tools assume that every learner can use the same rigid workflow: select a task, start a timer, and follow a fixed schedule. That approach can create unnecessary friction for neurodivergent students, whose attention, energy, sensory needs, and learning preferences may vary from day to day.

CogniFlow addresses this gap with an adaptive study experience. Instead of forcing students to configure multiple disconnected tools, it uses a network of specialized agents to interpret intent, recommend strategies, structure focus and recovery time, and coordinate study sessions with the student's calendar.

## Agent architecture

CogniFlow is built on **Fetch.ai uAgents** and **Agentverse**. A Director agent acts as the entry point and routes requests to the specialist agent best suited to handle them.

```text
                              +----------------------+
                              |      Student UI      |
                              | Profile • Dashboard  |
                              | Timer • Agent Graph   |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              |       Director       |
                              | Intent routing       |
                              | Request coordination |
                              +----+------------+----+
                                   |            |
                    +--------------+            +----------------+
                    v                                v
          +------------------+              +------------------+
          |      Insight     |              |      Rhythm      |
          | Learning         |              | Focus and break  |
          | strategies       |              | cycles           |
          +------------------+              +------------------+
                                   |
                                   v
                          +------------------+
                          |       Sync       |
                          | Calendar         |
                          | scheduling       |
                          +--------+---------+
                                   |
                                   v
                          +------------------+
                          | Study plan and   |
                          | scheduled session|
                          +------------------+
```

### Agents

| Agent | Responsibility |
| --- | --- |
| **Director** | Interprets user intent and routes requests across the agent network. |
| **Insight** | Recommends learning strategies adapted to the student's cognitive profile and current needs. |
| **Rhythm** | Creates focus and break cycles that support sustainable attention and momentum. |
| **Sync** | Coordinates study plans with Google Calendar and handles scheduling. |

## Features

- 🧠 **Cognitive profile onboarding** — A guided four-step flow captures the student's learning preferences, needs, and study context.
- 🤖 **Multi-agent coordination** — Four purpose-built uAgents collaborate through a clear routing and specialist-agent architecture.
- 🕸️ **Real-time agent network visualization** — See agent activity and coordination as requests move through the system.
- ⏱️ **Focus timer** — Start structured focus sessions with breaks powered by the Rhythm agent.
- 📊 **Study dashboard** — Access study guidance, session state, and agent activity from a focused sidebar layout.
- 📅 **Google Calendar integration** — Convert recommended study plans into scheduled calendar sessions through Sync.
- ♿ **Neurodivergent-first design** — Supports adaptive workflows for students with ADHD, dyslexia, autism, and anxiety.

## Tech stack

| Layer | Technology |
| --- | --- |
| Agent network | Fetch.ai uAgents, Agentverse |
| Frontend | React, Vite, Tailwind CSS v4 |
| Backend | FastAPI, Python |
| Scheduling | Google Calendar integration |
| Languages | Python, JavaScript, CSS |

## Getting started

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- npm
- Fetch.ai / Agentverse credentials configured as required by the project
- Google Calendar credentials for calendar functionality

### Installation

```bash
git clone https://github.com/SaiGadwe/cogniflow.git
cd cogniflow
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install and start the frontend in its own terminal:

```bash
cd frontend
npm install
npm run dev
```

### Run the agent network and backend

CogniFlow uses five terminals for local development. From the project directory, start each process in its own terminal:

```bash
# Terminal 1
make insight

# Terminal 2
make rhythm

# Terminal 3
make sync

# Terminal 4
make director

# Terminal 5
python server.py
```

Check each terminal's output for the local host, port, and connection status.

## Screenshots

Screenshots will be added here. Planned coverage includes:

- Cognitive profile onboarding
- Agent network visualization
- Focus timer
- Dashboard sidebar
- Google Calendar scheduling flow

## Hackathon

Built for the **Fetch.ai Autonomous Agent Challenge**.

## License

No license has been specified yet.
