.PHONY: help build start

# Default target
help:
	@echo "make build           - Builds the image and loads it into the local registry"
	@echo "make start           - Starts the container using docker compose"
	@echo "ARGS='...'           - Pass options to docker compose (e.g., make start ARGS='-d --build')"


# Detached start
build:
	@docker buildx build --tag wohnungsjaeger3000:latest --load .


# Start development environment
start:
	@docker compose up $(ARGS)

