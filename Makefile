#!make

dev:
	@uvicorn --reload --use-colors --host 0.0.0.0 --port 8000 --log-level debug "app.main:app"

format:
	@isort app
	@black app
	@pflake8 app

up:
	@docker-compose up -d --build
