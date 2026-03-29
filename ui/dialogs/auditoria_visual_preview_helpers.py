from __future__ import annotations

from PySide6.QtGui import QPixmap


def empty_preview_text(lado: str) -> str:
    return f"Sin imagen ({'frente' if lado == 'F' else 'dorso'})"


def viewport_preview_size(scroll) -> tuple[int, int]:
    vw = max(200, scroll.viewport().width() - 12)
    vh = max(200, scroll.viewport().height() - 12)
    return vw, vh


def is_stale_preview_response(
    *,
    lado: str,
    req_id: int,
    raw: str,
    preview_req_id: dict[str, int],
    last_preview_path: dict[str, str | None],
) -> bool:
    if req_id != preview_req_id.get(lado, 0):
        return True

    current_raw = last_preview_path.get(lado)
    if current_raw and current_raw != raw:
        return True

    return False


def extract_preview_error(err_text: str) -> str:
    lines = [l.strip() for l in (err_text or "").splitlines() if l.strip()]
    return lines[-1] if lines else "Error al cargar la imagen."


def pixmap_from_png_bytes(png_bytes: bytes):
    pix = QPixmap()
    ok = pix.loadFromData(png_bytes)
    if not ok or pix.isNull():
        return None
    return pix
