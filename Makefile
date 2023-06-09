#!make

dev:
	@uvicorn --reload --use-colors --host 0.0.0.0 --port 8000 --log-level debug "app.main:app"

format:
	@isort app
	@black app
	@pflake8 app

up:
	@docker compose up -d --build

down:
	@docker compose down

up-db:
	@docker compose up -d kucoin-redis
	@docker compose up -d kucoin-postgres

migration:
	@alembic upgrade head

create-migration:
	@alembic revision --autogenerate -m "$(filter-out $@, $(MAKECMDGOALS))"

down-migration:
	@alembic downgrade -1

%:
	@true
