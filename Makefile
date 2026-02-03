.PHONY: lint format

lint:
	isort . --check-only --diff
	black . --check
	flake8 .

format:
	isort .
	black .