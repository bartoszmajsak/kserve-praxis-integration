PYTHON ?= python3

.PHONY: build png check clean

# Regenerate docs/, site/ and build/artifact/ from src/ and tools/.
build:
	$(PYTHON) tools/build.py

# Render the light figures to docs/figs/png/. Needs rsvg-convert. Run it after a figure changed.
png:
	$(PYTHON) tools/png.py

# Build into a temporary directory and compare it with the committed docs/ and site/.
# The PNG figures are compared by the hash of the SVG they were rendered from.
check:
	@tmp="$$(mktemp -d)"; trap 'rm -rf "$$tmp"' EXIT; \
	$(PYTHON) tools/build.py --out "$$tmp" || exit 1; \
	stale=0; diff -r -x png docs "$$tmp/docs" || stale=1; diff -r site "$$tmp/site" || stale=1; \
	$(PYTHON) tools/png.py --check || stale=1; \
	if [ "$$stale" -eq 0 ]; then \
		echo "docs/ and site/ are up to date"; \
	else \
		echo "docs/ or site/ is out of date: run 'make build' and commit the result" >&2; exit 1; \
	fi

clean:
	rm -rf build tools/__pycache__
