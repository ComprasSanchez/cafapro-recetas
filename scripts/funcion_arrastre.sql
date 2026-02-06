CREATE OR REPLACE FUNCTION fn_arrastrar_excluidos_previos(p_recepcion_actual_id integer)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_prestador_id integer;
    v_obra_social_id integer;
    v_prev_recepcion_id integer;
    v_has_any boolean;
    v_moved integer := 0;
BEGIN
    -- Datos recepción actual
    SELECT r.prestador_id, r.obra_social_id
    INTO v_prestador_id, v_obra_social_id
    FROM recepcion r
    WHERE r.recepcion_id = p_recepcion_actual_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recepcion % no existe', p_recepcion_actual_id;
    END IF;

    -- Si ya tiene archivos, no duplicar
    SELECT EXISTS(
        SELECT 1 FROM archivo a WHERE a.recepcion_id = p_recepcion_actual_id
    )
    INTO v_has_any;

    IF v_has_any THEN
        RETURN 0;
    END IF;

    -- Recepción anterior (por recepcion_id)
    SELECT r.recepcion_id
    INTO v_prev_recepcion_id
    FROM recepcion r
    WHERE r.prestador_id = v_prestador_id
      AND r.obra_social_id = v_obra_social_id
      AND r.recepcion_id < p_recepcion_actual_id
    ORDER BY r.recepcion_id DESC
    LIMIT 1;

    IF v_prev_recepcion_id IS NULL THEN
        RETURN 0;
    END IF;

    -- Mover + reordenar, y contar movidos correctamente
    WITH cand AS (
        SELECT DISTINCT
            a.archivo_id,
            a.fecha,
            a.hora,
            a.nro_referencia
        FROM archivo a
        LEFT JOIN asociacion x
          ON x.archivo_id = a.archivo_id AND x.vigente IS TRUE
        LEFT JOIN recetas rc
          ON rc.receta_id = x.receta_id
        WHERE a.recepcion_id = v_prev_recepcion_id
          AND (x.asociacion_id IS NULL OR rc.estado_seguimiento_id = 3)
          AND a.vencido IS FALSE
    ),
    ranked AS (
        SELECT
            c.archivo_id,
            ROW_NUMBER() OVER (
                ORDER BY c.fecha ASC, c.hora ASC, c.nro_referencia ASC, c.archivo_id ASC
            ) AS nuevo_orden
        FROM cand c
    ),
    moved AS (
        UPDATE archivo a
        SET
            recepcion_id = p_recepcion_actual_id,
            orden_lote   = r.nuevo_orden
        FROM ranked r
        WHERE a.archivo_id = r.archivo_id
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_moved FROM moved;

    RETURN COALESCE(v_moved, 0);
END;
$$;
