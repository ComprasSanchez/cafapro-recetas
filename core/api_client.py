"""
Cliente HTTP compartido para la API principal de Cafapro.

Usa un httpx.Client singleton con connection pooling, de modo que las
conexiones TCP/TLS se reutilizan entre requests en lugar de abrirse de cero
cada vez (httpx top-level functions crean un cliente nuevo por request).

httpx.Client es thread-safe: soporta acceso concurrente desde múltiples hilos
(ServiceJob, ThreadPoolExecutor, etc.) sin necesidad de locks externos.

Uso en los servicios:
    from core.api_client import get_client, TIMEOUT_HEAVY

    resp = get_client().get(url)
    resp = get_client().post(url, json=payload)
    resp = get_client().post(url, json=payload, timeout=TIMEOUT_HEAVY)
"""
from __future__ import annotations

import threading

import httpx

# connect y pool siempre cortos — si el servidor no responde al conectar,
# no tiene sentido esperar. read varía según la operación.
TIMEOUT_NORMAL = httpx.Timeout(connect=5.0, read=60.0,  write=60.0,  pool=5.0)
TIMEOUT_HEAVY  = httpx.Timeout(connect=5.0, read=600.0, write=600.0, pool=5.0)

_lock: threading.Lock = threading.Lock()
_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    """
    Retorna el cliente HTTP compartido, creándolo si es necesario.
    El cliente mantiene un pool de hasta 10 conexiones keep-alive hacia
    la API, con expiración de 30 segundos de inactividad.
    """
    global _client
    if _client is None or _client.is_closed:
        with _lock:
            if _client is None or _client.is_closed:
                _client = httpx.Client(
                    timeout=TIMEOUT_NORMAL,
                    limits=httpx.Limits(
                        max_keepalive_connections=10,
                        max_connections=20,
                        keepalive_expiry=30.0,
                    ),
                )
    return _client


def close_client() -> None:
    """Cierra el cliente y libera todas las conexiones. Llamar al salir de la app."""
    global _client
    with _lock:
        if _client is not None and not _client.is_closed:
            _client.close()
            _client = None
