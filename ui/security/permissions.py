from __future__ import annotations

from typing import Any


ADMIN_ROLE_ID = 1
AUDITOR_ROLE_ID = 2

ALLOWED_AUDITOR_ACTION_KEYS = {
    "carga_recepcion_tab",
    "archivo_cvs_tab",
    "tab_auditoria",
    "toggle_theme",
}

ALLOWED_AUDITOR_TAB_KEYS = {
    "carga-recepcion-handler",
    "archivo-cvs",
    "auditoria",
}


def get_role_id(user: Any) -> int | None:
    raw = getattr(user, "rol_id", None)
    if raw is None:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def is_admin(user: Any) -> bool:
    return get_role_id(user) == ADMIN_ROLE_ID


def is_auditor(user: Any) -> bool:
    return get_role_id(user) == AUDITOR_ROLE_ID


def can_access_tab(*, user: Any, tab_key: str | None) -> bool:
    if is_admin(user):
        return True
    if is_auditor(user):
        return str(tab_key or "") in ALLOWED_AUDITOR_TAB_KEYS
    return False


def can_access_header_action(
    *,
    user: Any,
    action_key: str,
    kind: str,
    tab_key: str | None = None,
) -> bool:
    if is_admin(user):
        return True

    if is_auditor(user):
        key = str(action_key or "")
        if key in ALLOWED_AUDITOR_ACTION_KEYS:
            return True
        if kind == "tab":
            return can_access_tab(user=user, tab_key=tab_key)
        return False

    return False


def can_open_carga_debitos_excluidos(user: Any) -> bool:
    return is_admin(user)


def can_cerrar_recepcion(user: Any) -> bool:
    return is_admin(user)
