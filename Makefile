
.PHONY: test test-cov publish publish-openai publish-anthropic publish-wandb publish-error-reports publish-reviewer publish-rate-limit tag-version tag-version-openai tag-version-anthropic tag-version-wandb tag-version-error-reports tag-version-reviewer tag-version-rate-limit release release-openai release-anthropic release-wandb release-error-reports release-reviewer release-rate-limit sync setup-all

sync:
	uv venv
	uv sync
	uv pip install tqdm

setup-all:
	cd packages/openai_support && uv sync --group dev
	cd packages/anthropic && uv sync --group dev
	cd packages/wandb && uv sync --group dev
	cd packages/error_reports && uv sync --group dev
	cd packages/reviewer && uv sync --group dev
	cd packages/rate_limit && uv sync --group dev

test:
	cd test && uv run pytest
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests
	cd packages/anthropic && uv sync --group dev && uv run -m pytest tests
	cd packages/wandb && uv sync --group dev && uv run -m pytest tests
	cd packages/error_reports && uv sync --group dev && uv run -m pytest tests
	cd packages/reviewer && uv sync --group dev && uv run -m pytest tests
	cd packages/rate_limit && uv sync --group dev && uv run -m pytest tests

test-cov:
	cd test && uv run pytest -v --cov=pinjected --cov-report=xml
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests

publish:
	uv build
	uv pip publish dist/*.whl dist/*.tar.gz

publish-openai:
	cd packages/openai_support && uv build
	cd packages/openai_support && uv pip publish dist/*.whl dist/*.tar.gz

publish-anthropic:
	cd packages/anthropic && uv build
	cd packages/anthropic && uv pip publish dist/*.whl dist/*.tar.gz

publish-wandb:
	cd packages/wandb && uv build
	cd packages/wandb && uv pip publish dist/*.whl dist/*.tar.gz

publish-error-reports:
	cd packages/error_reports && uv build
	cd packages/error_reports && uv pip publish dist/*.whl dist/*.tar.gz

publish-reviewer:
	cd packages/reviewer && uv build
	cd packages/reviewer && uv pip publish dist/*.whl dist/*.tar.gz

publish-rate-limit:
	cd packages/rate_limit && uv build
	cd packages/rate_limit && uv pip publish dist/*.whl dist/*.tar.gz

tag-version:
	git tag v$(shell grep -m 1 version pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-openai:
	git tag pinjected-openai-v$(shell grep -m 1 version packages/openai_support/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-anthropic:
	git tag pinjected-anthropic-v$(shell grep -m 1 version packages/anthropic/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-wandb:
	git tag pinjected-wandb-v$(shell grep -m 1 version packages/wandb/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-error-reports:
	git tag pinjected-error-reports-v$(shell grep -m 1 version packages/error_reports/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-reviewer:
	git tag pinjected-reviewer-v$(shell grep -m 1 version packages/reviewer/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-rate-limit:
	git tag pinjected-rate-limit-v$(shell grep -m 1 version packages/rate_limit/pyproject.toml | cut -d'"' -f2)
	git push --tags

release: tag-version publish
release-openai: tag-version-openai publish-openai
release-anthropic: tag-version-anthropic publish-anthropic
release-wandb: tag-version-wandb publish-wandb
release-error-reports: tag-version-error-reports publish-error-reports
release-reviewer: tag-version-reviewer publish-reviewer
release-rate-limit: tag-version-rate-limit publish-rate-limit
