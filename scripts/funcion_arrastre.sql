CREATE OR REPLACE FUNCTION fn_arrastrar_excluidos_previos(p_recepcion_actual_id integer)
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_prestador_id integer;
            v_obra_social_id integer;
            v_fecha_presentacion timestamp;
            v_prev_recepcion_id integer;
            v_cutoff_ts timestamp;
            v_has_any boolean;
            v_moved integer := 0;
        BEGIN
            -- 1) Cargar datos de recepción actual
            SELECT r.prestador_id, r.obra_social_id, r.fecha_presentacion
            INTO v_prestador_id, v_obra_social_id, v_fecha_presentacion
            FROM recepcion r
            WHERE r.recepcion_id = p_recepcion_actual_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Recepcion % no existe', p_recepcion_actual_id;
            END IF;

            -- 2) Guard: si la recepción ya tiene archivos, no recalcular
            SELECT EXISTS(
                SELECT 1
                FROM archivo a
                WHERE a.recepcion_id = p_recepcion_actual_id
            )
            INTO v_has_any;

            IF v_has_any THEN
                RETURN 0;
            END IF;

            -- 3) Buscar recepción anterior inmediata (mismo prestador + obra social)
            SELECT r.recepcion_id
            INTO v_prev_recepcion_id
            FROM recepcion r
            WHERE r.prestador_id = v_prestador_id
              AND r.obra_social_id = v_obra_social_id
              AND r.fecha_presentacion < v_fecha_presentacion
            ORDER BY r.fecha_presentacion DESC
            LIMIT 1;

            IF v_prev_recepcion_id IS NULL THEN
                RETURN 0;
            END IF;

            -- 4) Cutoff de vencimiento: fecha_presentacion_actual - 60 días
            v_cutoff_ts := v_fecha_presentacion - INTERVAL '60 days';

            -- 5) Mover excluidos NO vencidos + renumerar orden_lote = 1..K
            WITH cand AS (
                SELECT
                    a.archivo_id,
                    a.fecha,
                    a.hora,
                    a.nro_referencia
                FROM archivo a
                LEFT JOIN asociacion x
                    ON x.archivo_id = a.archivo_id
                   AND x.vigente IS TRUE
                LEFT JOIN recetas rc
                    ON rc.receta_id = x.receta_id
                WHERE a.recepcion_id = v_prev_recepcion_id
                  AND (x.asociacion_id IS NULL OR rc.estado_seguimiento_id = 3)
                  AND (a.fecha::timestamp + a.hora) >= v_cutoff_ts
            ),
            ranked AS (
                SELECT
                    c.archivo_id,
                    ROW_NUMBER() OVER (
                        ORDER BY c.fecha ASC,
                                 c.hora ASC,
                                 c.nro_referencia ASC,
                                 c.archivo_id ASC
                    ) AS nuevo_orden
                FROM cand c
            )
            UPDATE archivo a
            SET
                recepcion_id = p_recepcion_actual_id,
                orden_lote   = r.nuevo_orden
            FROM ranked r
            WHERE a.archivo_id = r.archivo_id;

            GET DIAGNOSTICS v_moved = ROW_COUNT;
            RETURN COALESCE(v_moved, 0);
        END;
        $$;