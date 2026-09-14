from pathlib import Path


def normalize_path(path_value):
    """Normalize user-supplied filesystem paths.

    Some shells and environment values may include backslash-escaped spaces, e.g.
    "/Users/.../Mobile\\ Documents/...". These are equivalent to the real path but
    can cause writes to a different directory. Normalize them before resolution.
    """
    if path_value is None:
        return None

    text = str(path_value).strip()
    if not text:
        return Path(text)

    candidate = Path(text.replace('\\ ', ' '))
    return candidate.expanduser().resolve()
