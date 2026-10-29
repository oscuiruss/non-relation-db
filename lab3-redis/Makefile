.PHONY: up down logs smoke test load

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app redis

smoke:
	./scripts/smoke-test.sh

test:
	PYTHONPATH=. python3 -m unittest discover -s tests -v

load:
	docker compose --profile load run --rm k6
