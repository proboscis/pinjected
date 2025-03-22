
.PHONY: test test-cov publish publish-openai tag-version tag-version-openai release release-openai sync setup-all

sync:
	uv venv
	uv sync
	uv pip install tqdm

setup-all:
	cd packages/openai_support && uv sync --group dev

test:
	cd test && uv run pytest
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests

test-cov:
	cd test && uv run pytest -v --cov=pinjected --cov-report=xml
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests

publish:
	uv build
	uv publish

publish-openai:
	cd packages/openai_support && uv build
	cd packages/openai_support && uv publish

tag-version:
	git tag v$(shell grep -m 1 version pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-openai:
	git tag pinjected-openai-v$(shell grep -m 1 version packages/openai_support/pyproject.toml | cut -d'"' -f2)
	git push --tags

release: tag-version publish
release-openai: tag-version-openai publish-openai
