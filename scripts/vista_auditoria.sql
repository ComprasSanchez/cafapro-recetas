DROP VIEW IF EXISTS vw_archivo_resumen_auditoria;

CREATE OR REPLACE VIEW vw_archivo_resumen_auditoria AS

WITH receta_match_en_esta_recepcion AS (
    SELECT
        ar.archivo_id,
        x.asociacion_id,
        x.receta_id
    FROM archivo ar
    LEFT JOIN LATERAL (
        SELECT a.asociacion_id, a.receta_id
        FROM asociacion a
        JOIN recetas r
          ON r.receta_id = a.receta_id
        WHERE a.archivo_id = ar.archivo_id
          AND a.vigente IS TRUE
          AND ar.recepcion_id IS NOT NULL
          AND r.recepcion_id = ar.recepcion_id
        ORDER BY a.asociacion_id DESC
        LIMIT 1
    ) x ON TRUE
),

asoc_flags AS (
    SELECT
        ar.archivo_id,

        EXISTS (
            SELECT 1
            FROM asociacion a
            JOIN recetas r ON r.receta_id = a.receta_id
            WHERE a.archivo_id = ar.archivo_id
              AND a.vigente IS TRUE
              AND ar.recepcion_id IS NOT NULL
              AND r.recepcion_id = ar.recepcion_id
        ) AS tiene_asoc_en_esta_recepcion,

        EXISTS (
            SELECT 1
            FROM asociacion a
            JOIN recetas r ON r.receta_id = a.receta_id
            WHERE a.archivo_id = ar.archivo_id
              AND a.vigente IS TRUE
              AND ar.recepcion_id IS NOT NULL
              AND r.recepcion_id <> ar.recepcion_id
        ) AS tiene_asoc_en_otra_recepcion

    FROM archivo ar
),

troq_agregado AS (
    SELECT
        m.archivo_id,
        COALESCE(SUM(t.monto::numeric * t.cantidad::numeric),0)::numeric(12,2) AS importe_reconocido
    FROM receta_match_en_esta_recepcion m
    JOIN troqueles t
      ON t.receta_id = m.receta_id
    GROUP BY m.archivo_id
),

receta_existe_por_archivo AS (
    SELECT
        ar.archivo_id,
        CASE
            WHEN ar.recepcion_id IS NULL THEN FALSE
            ELSE EXISTS (
                SELECT 1
                FROM recetas r
                WHERE r.recepcion_id = ar.recepcion_id
                  AND r.nro_receta::text = ar.nro_receta::text
                  AND r.vigente IS TRUE
            )
        END AS existe_receta
    FROM archivo ar
),

union_data AS (

-- ======================================
-- ARCHIVOS
-- ======================================

SELECT
    ar.archivo_id,
    m.asociacion_id,
    m.receta_id,
    ar.recepcion_id,

    ar.nro_receta     AS numero_receta,
    ar.nro_referencia AS numero_referencia,
    ar.orden_lote     AS nro_lote,

    TRUE AS existe_archivo,
    COALESCE(re.existe_receta, FALSE) AS existe_receta,

    COALESCE(ta.importe_reconocido,0)::numeric(12,2) AS importe_reconocido,
    COALESCE(ar.importe_bruto,0)::numeric(12,2)      AS importe_oficial,

    r.estado_receta_id,
    er.descripcion AS estado_receta,

    r.ubicacion_frente AS frente_jpg,

    CASE
        WHEN m.receta_id IS NULL THEN FALSE
        ELSE EXISTS (
            SELECT 1
            FROM debitos d
            WHERE d.receta_id = m.receta_id
        )
    END AS flag_debitos,

    af.tiene_asoc_en_esta_recepcion,
    af.tiene_asoc_en_otra_recepcion

FROM archivo ar
LEFT JOIN receta_match_en_esta_recepcion m
    ON m.archivo_id = ar.archivo_id

LEFT JOIN recetas r
    ON r.receta_id = m.receta_id

LEFT JOIN estado_receta er
    ON er.estado_receta_id = r.estado_receta_id

LEFT JOIN troq_agregado ta
    ON ta.archivo_id = ar.archivo_id

LEFT JOIN receta_existe_por_archivo re
    ON re.archivo_id = ar.archivo_id

LEFT JOIN asoc_flags af
    ON af.archivo_id = ar.archivo_id


UNION ALL


-- ======================================
-- RECETAS SIN ASOCIACION (cualquier estado)
-- ======================================

SELECT
    NULL AS archivo_id,
    NULL AS asociacion_id,
    r.receta_id,
    r.recepcion_id,

    r.nro_receta AS numero_receta,
    NULL AS numero_referencia,
    NULL AS nro_lote,

    FALSE AS existe_archivo,
    TRUE  AS existe_receta,

    0::numeric(12,2) AS importe_reconocido,
    0::numeric(12,2) AS importe_oficial,

    r.estado_receta_id,
    er.descripcion AS estado_receta,

    r.ubicacion_frente AS frente_jpg,

    EXISTS (
        SELECT 1
        FROM debitos d
        WHERE d.receta_id = r.receta_id
    ) AS flag_debitos,
    FALSE AS tiene_asoc_en_esta_recepcion,
    FALSE AS tiene_asoc_en_otra_recepcion

FROM recetas r
LEFT JOIN estado_receta er
    ON er.estado_receta_id = r.estado_receta_id

WHERE r.vigente IS TRUE
AND NOT EXISTS (
    SELECT 1
    FROM asociacion a
    WHERE a.receta_id = r.receta_id
      AND a.vigente IS TRUE
)

)

SELECT
    row_number() OVER() AS row_id,
    *
FROM union_data;
