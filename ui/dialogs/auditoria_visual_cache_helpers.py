from __future__ import annotations


def put_preview_cache_item(
    preview_cache: dict[str, bytes],
    *,
    raw: str,
    img_bytes: bytes,
    max_items: int,
) -> None:
    if not img_bytes:
        return

    if raw in preview_cache:
        return

    if len(preview_cache) >= int(max_items):
        preview_cache.pop(next(iter(preview_cache)))

    preview_cache[raw] = img_bytes
