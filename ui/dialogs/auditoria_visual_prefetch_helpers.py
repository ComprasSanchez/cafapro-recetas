from __future__ import annotations


def build_prefetch_queue(
    *,
    asociacion_ids: list[int],
    current_index: int,
    prefetch_size: int,
    cached_ids: set[int],
    loading_ids: set[int],
) -> list[int]:
    if not asociacion_ids:
        return []

    total = len(asociacion_ids)
    if total <= 1:
        return []

    idx = max(0, min(int(current_index), total - 1))
    current_id = int(asociacion_ids[idx])
    queue: list[int] = []

    step = 1
    while len(queue) < int(prefetch_size) and step < total:
        for delta in (step, -step):
            j = idx + delta
            if j < 0 or j >= total:
                continue

            asociacion_id = int(asociacion_ids[j])
            if asociacion_id == current_id:
                continue
            if asociacion_id in cached_ids:
                continue
            if asociacion_id in loading_ids:
                continue
            if asociacion_id in queue:
                continue

            queue.append(asociacion_id)
            if len(queue) >= int(prefetch_size):
                break

        step += 1

    return queue


def pop_next_prefetch(
    queue: list[int],
    *,
    cached_ids: set[int],
    loading_ids: set[int],
) -> int | None:
    while queue:
        candidate = int(queue.pop(0))
        if candidate in cached_ids:
            continue
        if candidate in loading_ids:
            continue
        return candidate

    return None
