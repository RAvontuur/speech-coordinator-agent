from pathlib import Path


def normalize_path(path_value):
    """Normalize user-supplied filesystem paths."""
    if path_value is None:
        return None
    text = str(path_value).strip()
    if not text:
        return Path(text)
    return Path(text.replace("\\ ", " ")).expanduser().resolve()