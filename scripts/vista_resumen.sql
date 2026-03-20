DROP VIEW IF EXISTS vw_resumen_recepcion;

CREATE OR REPLACE VIEW vw_resumen_recepcion AS
WITH archivos_validos AS (
    SELECT
        r1.recepcion_id,
        r1.prestador_id,
        r1.periodo_id,
        a.archivo_id,
        a.importe_bruto,
        a.importe_cobertura,
        a.importe_afiliado
    FROM recepcion r1
    JOIN archivo a
        ON a.recepcion_id = r1.recepcion_id
    WHERE EXISTS (
        SELECT 1
        FROM asociacion x
        JOIN recetas rc
            ON rc.receta_id = x.receta_id
        WHERE x.archivo_id = a.archivo_id
          AND x.vigente IS TRUE
          AND rc.estado_seguimiento_id IS DISTINCT FROM 3
          AND rc.estado_receta_id = 1
    )
),
sum_archivos AS (
    SELECT
        av.recepcion_id,
        av.prestador_id,
        av.periodo_id,
        COALESCE(SUM(av.importe_bruto), 0)::numeric(12,2)       AS total_bruto,
        COALESCE(SUM(av.importe_cobertura), 0)::numeric(12,2)   AS total_cobertura,
        COALESCE(SUM(av.importe_afiliado), 0)::numeric(12,2)    AS total_afiliado
    FROM archivos_validos av
    GROUP BY av.recepcion_id, av.prestador_id, av.periodo_id
),
recetas_validas AS (
    SELECT
        r1.recepcion_id,
        r1.prestador_id,
        r1.periodo_id,
        COUNT(DISTINCT rc.receta_id) AS cantidad_recetas
    FROM recepcion r1
    JOIN archivo a
        ON a.recepcion_id = r1.recepcion_id
    JOIN asociacion x
        ON x.archivo_id = a.archivo_id
       AND x.vigente IS TRUE
    JOIN recetas rc
        ON rc.receta_id = x.receta_id
    WHERE rc.estado_seguimiento_id IS DISTINCT FROM 3
      AND rc.estado_receta_id = 1
    GROUP BY r1.recepcion_id, r1.prestador_id, r1.periodo_id
)
SELECT
    r.prestador_id,
    r.recepcion_id,
    r.periodo_id,
    r.numero AS recepcion_numero,
    r.fecha_presentacion,
    r.estado_recepcion_id,
    COALESCE(rv.cantidad_recetas, 0::bigint)                  AS cantidad_recetas,
    COALESCE(sa.total_bruto, 0::numeric)::numeric(12,2)       AS total_bruto,
    COALESCE(sa.total_cobertura, 0::numeric)::numeric(12,2)   AS total_cobertura,
    COALESCE(sa.total_afiliado, 0::numeric)::numeric(12,2)    AS total_afiliado
FROM recepcion r
LEFT JOIN recetas_validas rv
    ON rv.recepcion_id = r.recepcion_id
   AND rv.prestador_id = r.prestador_id
   AND rv.periodo_id = r.periodo_id
LEFT JOIN sum_archivos sa
    ON sa.recepcion_id = r.recepcion_id
   AND sa.prestador_id = r.prestador_id
   AND sa.periodo_id = r.periodo_id;
