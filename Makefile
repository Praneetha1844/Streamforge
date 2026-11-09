.PHONY: install lint format typecheck test check demo up down tf-check

install:
	pip install -e ".[dev,postgres,pubsub,otel]"
	pre-commit install

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

typecheck:
	mypy

test:
	pytest --cov --cov-report=term-missing

check: lint typecheck test

demo:
	streamforge run --demo 200 --seed 7

up:
	docker compose up --build -d

down:
	docker compose down

tf-check:
	terraform -chdir=infra/terraform fmt -check -recursive
	terraform -chdir=infra/terraform init -backend=false
	terraform -chdir=infra/terraform validate
