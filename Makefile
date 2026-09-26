.PHONY: director insight rhythm sync all

insight:
	python -m agents.insight_agent.insight_agent

rhythm:
	python -m agents.rhythm_agent.rhythm_agent

sync:
	python -m agents.sync_agent.sync_agent

director:
	python -m agents.director_agent.director_agent

all:
	@echo "Run each in a separate terminal:"
	@echo "  make insight     # Terminal 1 (port 8001)"
	@echo "  make rhythm      # Terminal 2 (port 8002)"
	@echo "  make sync        # Terminal 3 (port 8004)"
	@echo "  make director    # Terminal 4 (port 8003, start last)"