
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
	@echo "Checking if packages are already published..."
	@for pkg in dist/*.whl; do \
		PKG_NAME=$$(echo $$pkg | sed -E 's/.*\/([^\/]*)-[0-9].*/\1/'); \
		PKG_VERSION=$$(echo $$pkg | sed -E 's/.*-([0-9][^-]*)(\.tar\.gz|\.whl)/\1/'); \
		echo "Checking $$PKG_NAME version $$PKG_VERSION"; \
		HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/$$PKG_NAME/$$PKG_VERSION/json); \
		if [ "$$HTTP_CODE" = "404" ]; then \
			echo "Publishing $$pkg..."; \
			uv publish $$pkg; \
		else \
			echo "Package $$PKG_NAME version $$PKG_VERSION already published, skipping."; \
		fi; \
	done

publish-openai:
	cd packages/openai_support && uv build
	@echo "Checking if openai packages are already published..."
	@for pkg in dist/pinjected_openai-*.whl; do \
		PKG_NAME="pinjected-openai"; \
		PKG_VERSION=$$(echo $$pkg | sed -E 's/.*-([0-9][^-]*)(\.tar\.gz|\.whl)/\1/'); \
		echo "Checking $$PKG_NAME version $$PKG_VERSION"; \
		HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/$$PKG_NAME/$$PKG_VERSION/json); \
		if [ "$$HTTP_CODE" = "404" ]; then \
			echo "Publishing $$pkg..."; \
			uv publish $$pkg; \
		else \
			echo "Package $$PKG_NAME version $$PKG_VERSION already published, skipping."; \
		fi; \
	done

tag-version:
	git tag v$(shell grep -m 1 version pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-openai:
	git tag pinjected-openai-v$(shell grep -m 1 version packages/openai_support/pyproject.toml | cut -d'"' -f2)
	git push --tags

release: tag-version publish
release-openai: tag-version-openai publish-openai
