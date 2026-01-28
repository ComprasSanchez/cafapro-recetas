CREATE OR REPLACE VIEW vw_archivo_resumen_auditoria AS
WITH receta_por_archivo AS (
    SELECT
        a.archivo_id,
        MIN(a.asociacion_id) AS asociacion_id,
        MIN(a.receta_id)     AS receta_id
    FROM asociacion a
    GROUP BY a.archivo_id
),
troq_agregado AS (
    SELECT
        rpa.archivo_id,
        COALESCE(SUM(t.monto::numeric * t.cantidad::numeric), 0)::numeric(12,2) AS importe_reconocido
    FROM receta_por_archivo rpa
    JOIN troqueles t
      ON t.receta_id = rpa.receta_id
    GROUP BY rpa.archivo_id
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
            )
        END AS existe_receta
    FROM archivo ar
)
SELECT
    ar.archivo_id,
    rpa.asociacion_id,
    ar.recepcion_id,
    ar.nro_receta     AS numero_receta,
    ar.nro_referencia AS numero_referencia,
    ar.orden_lote     AS nro_lote,
    TRUE              AS existe_archivo,
    COALESCE(re.existe_receta, FALSE) AS existe_receta,
    COALESCE(ta.importe_reconocido, 0)::numeric(12,2) AS importe_reconocido,
    COALESCE(ar.importe_obs, 0)::numeric(12,2)        AS importe_oficial,
    r.estado_receta_id AS estado_receta_id,
    er.descripcion     AS estado_receta,
    r.ubicacion_frente AS frente_jpg,
        CASE
        WHEN rpa.receta_id IS NULL THEN FALSE
        ELSE EXISTS (
            SELECT 1
            FROM debitos d
            WHERE d.receta_id = rpa.receta_id
        )
    END AS flag_debitos
FROM archivo ar
LEFT JOIN receta_por_archivo rpa
  ON rpa.archivo_id = ar.archivo_id
LEFT JOIN recetas r
  ON r.receta_id = rpa.receta_id
LEFT JOIN estado_receta er
  ON er.estado_receta_id = r.estado_receta_id
LEFT JOIN troq_agregado ta
  ON ta.archivo_id = ar.archivo_id
LEFT JOIN receta_existe_por_archivo re
  ON re.archivo_id = ar.archivo_id;