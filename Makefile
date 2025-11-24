.PHONY: help install test format lint clean run bundle setup-dev setup-bundle

help:
	@echo "Available commands:"
	@echo "  make setup-dev    - Setup for local development (venv)"
	@echo "  make setup-bundle - Setup for bundling (lib/ folder)"
	@echo "  make bundle       - Create .mcpb bundle file"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make run          - Run MCP server"

setup-dev:
	./setup.sh

setup-bundle:
	./setup.sh --bundle

bundle: setup-bundle
	@echo "Creating .mcpb bundle..."
	rm -f ErcotMCPExtension.mcpb
	zip -r ErcotMCPExtension.mcpb manifest.json server/ lib/ requirements.txt README.md INSTALLATION.md universe_logo_small.png assets/
	@echo "✓ Bundle created: ErcotMCPExtension.mcpb ($$(du -h ErcotMCPExtension.mcpb | cut -f1))"
	@shasum -a 256 ErcotMCPExtension.mcpb

test:
	python3 -m pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf lib/
	rm -rf venv/
	rm -rf *.egg-info
	rm -f ErcotMCPExtension.mcpb
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	PYTHONPATH=.:./lib python3 -m server
