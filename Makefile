.PHONY: setup schema seed test run

setup: venv deps schema seed            ## full initial setup
	@echo "Setup complete. Run 'make run'."

venv:
	python3 -m venv .venv

deps:
	.venv/bin/pip install -q -r requirements.txt

schema:
	psql "$$DATABASE_URL" -f schema.sql

seed:
	@psql "$$DATABASE_URL" -c 'SELECT 1' >/dev/null 2>&1 || { echo 'DATABASE_URL not reachable'; exit 1; }
	.venv/bin/python seed_supabase.py --dsn "$$DATABASE_URL"

test:
	.venv/bin/python -m pytest tests/ -q

run:
	.venv/bin/python run.py
