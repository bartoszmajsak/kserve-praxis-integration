PYTHON ?= python3

.PHONY: build check clean

# Regenerate docs/, site/ and build/artifact/ from src/ and tools/.
build:
	$(PYTHON) tools/build.py

# Build into a temporary directory and compare it with the committed docs/ and site/.
check:
	@tmp="$$(mktemp -d)"; trap 'rm -rf "$$tmp"' EXIT; \
	$(PYTHON) tools/build.py --out "$$tmp" || exit 1; \
	stale=0; diff -r docs "$$tmp/docs" || stale=1; diff -r site "$$tmp/site" || stale=1; \
	if [ "$$stale" -eq 0 ]; then \
		echo "docs/ and site/ are up to date"; \
	else \
		echo "docs/ or site/ is out of date: run 'make build' and commit the result" >&2; exit 1; \
	fi

clean:
	rm -rf build tools/__pycache__
