format:
	poetry run ruff format

check-format:
	poetry run ruff format --check --diff

lint: format
	poetry run ruff check --fix

check-lint: check-format
	poetry run ruff check
