
.PHONY: test

test:
	cd test; poetry run pytest

publish:
	xonsh publish.xsh