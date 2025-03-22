
.PHONY: test test-cov publish tag-version release sync

sync:
	uv venv
	uv pip install -e .
	uv pip install tqdm

test:
	cd test; uv run pytest

test-cov:
	cd test; uv run pytest -v --cov=pinjected --cov-report=xml

publish:
	uv build
	uv pip publish dist/*.whl dist/*.tar.gz

tag-version:
	git tag v$(shell grep -m 1 version pyproject.toml | cut -d'"' -f2)
	git push --tags

release: tag-version publish
