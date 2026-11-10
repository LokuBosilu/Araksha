.PHONY: setup test ingest backtest forecast export app clean

setup:
	@echo "Setting up Silent Node environment..."
	npm install
	@echo "Environment ready."

test:
	@echo "Running test suite..."
	python3 -m unittest discover -s tests -p "test_*.py"

ingest:
	@echo "Ingesting case data and static covariates..."
	python3 scripts/ingest_cases.py
	python3 scripts/ingest_weather.py
	python3 scripts/build_static_covariates.py

backtest:
	@echo "Running rolling-origin backtest (2022-2026)..."
	python3 scripts/run_backtest.py

forecast:
	@echo "Executing operational forecast engine..."
	python3 scripts/run_forecast.py

export: forecast
	@echo "Exporting dashboard JSON data..."
	python3 scripts/export_dashboard_data.py

app:
	@echo "Starting Silent Node Web Dashboard..."
	npm run dev

clean:
	rm -rf dist build *.egg-info .pytest_cache
