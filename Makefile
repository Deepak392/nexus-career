.PHONY: up down build logs ps migrate makemigrations shell test clean

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

shell:
	docker compose exec backend python manage.py shell

test:
	docker compose exec backend python manage.py test

clean:
	@echo "WARNING: this deletes the local database volume."
	docker compose down -v