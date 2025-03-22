
.PHONY: test

test:
	cd test; uv run pytest

publish:
	xonsh publish.xsh
