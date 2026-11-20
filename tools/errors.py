"""How the build reports a problem in `src/` or `tools/`."""


class BuildError(Exception):
    pass


def require(ok, message):
    """Stop the build with `message` unless `ok` holds."""
    if not ok:
        raise BuildError(message)
