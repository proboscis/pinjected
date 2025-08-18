
.PHONY: test test-all test-cov publish publish-openai publish-anthropic publish-wandb publish-error-reports publish-reviewer publish-rate-limit publish-niji-voice publish-injected-utils publish-gcp tag-version tag-version-openai tag-version-anthropic tag-version-wandb tag-version-error-reports tag-version-reviewer tag-version-rate-limit tag-version-niji-voice tag-version-injected-utils tag-version-gcp release release-openai release-anthropic release-wandb release-error-reports release-reviewer release-rate-limit release-niji-voice release-injected-utils release-gcp sync setup-all setup-pre-commit

setup-pre-commit:
	@echo "Setting up pre-commit hooks..."
	@uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

sync:
	rm -rf packages/wandb
	uv venv
	uv sync --group dev
	uv pip install tqdm
	uv run --package pinjected-reviewer -- pinjected-reviewer uninstall
	@echo "Setting up pre-commit hooks..."
	$(MAKE) setup-pre-commit

lint:
	uvx ruff check
	uv run flake8

setup-all:
	cd packages/openai_support && uv sync --group dev
	cd packages/anthropic && uv sync --group dev
	cd packages/wandb_util && uv sync --group dev
	cd packages/error_reports && uv sync --group dev
	cd packages/reviewer && uv sync --group dev
	cd packages/rate_limit && uv sync --group dev
	cd packages/niji_voice && uv sync --group dev
	cd packages/injected_utils && uv sync --group dev
	cd packages/gcp && uv sync --group dev
	cd packages/pytest_runner && uv sync --group dev
	cd packages/pinjected-linter && uv sync --group dev

test:
	@echo "Running tests with lock mechanism to prevent concurrent execution..."
	@uv run python scripts/test_runner_with_lock.py --make-test

test-all:
	uv sync --all-packages
	uv run python scripts/test_runner_with_lock.py .
	cd packages/openai_support && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/anthropic && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/wandb_util && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/error_reports && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/reviewer && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/rate_limit && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/niji_voice && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/injected_utils && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/gcp && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/pytest_runner && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	cd packages/pinjected-linter && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests
	$(MAKE) test-linter
	$(MAKE) lint-with-pinjected-linter
	uv sync --group dev --all-packages

test-linter:
	cd packages/pinjected-linter/rust-poc && cargo test

build-linter:
	cd packages/pinjected-linter/rust-poc && cargo build --release

lint-with-pinjected-linter:
	cd packages/pinjected-linter/rust-poc && cargo build --release
	./packages/pinjected-linter/rust-poc/target/release/pinjected-linter pinjected/ packages/ --output-format terminal


test-cov:
	uv run python scripts/test_runner_with_lock.py . -v
	cd packages/openai_support && uv sync --group dev && uv run python ../../scripts/test_runner_with_lock.py tests

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

publish-anthropic:
	cd packages/anthropic && uv build
	cd packages/anthropic && uv pip publish dist/*.whl dist/*.tar.gz

publish-wandb:
	cd packages/wandb_util && uv build
	cd packages/wandb_util && uv pip publish dist/*.whl dist/*.tar.gz

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
	git tag pinjected-wandb-v$(shell grep -m 1 version packages/wandb_util/pyproject.toml | cut -d'"' -f2)
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

publish-niji-voice:
	cd packages/niji_voice && uv build
	cd packages/niji_voice && uv pip publish dist/*.whl dist/*.tar.gz

publish-injected-utils:
	cd packages/injected_utils && uv build
	cd packages/injected_utils && uv pip publish dist/*.whl dist/*.tar.gz

tag-version-niji-voice:
	git tag pinjected-niji-voice-v$(shell grep -m 1 version packages/niji_voice/pyproject.toml | cut -d'"' -f2)
	git push --tags

tag-version-injected-utils:
	git tag injected-utils-v$(shell grep -m 1 version packages/injected_utils/pyproject.toml | cut -d'"' -f2)
	git push --tags

release-niji-voice: tag-version-niji-voice publish-niji-voice
release-injected-utils: tag-version-injected-utils publish-injected-utils

publish-gcp:
	cd packages/gcp && uv build
	cd packages/gcp && uv pip publish dist/*.whl dist/*.tar.gz

tag-version-gcp:
	git tag pinjected-gcp-v$(shell grep -m 1 version packages/gcp/pyproject.toml | cut -d'"' -f2)
	git push --tags

release-gcp: tag-version-gcp publish-gcp
