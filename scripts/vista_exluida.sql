CREATE OR REPLACE VIEW vw_archivos_excluidos AS
SELECT
    a.recepcion_id,
    a.nro_referencia,
    a.nro_receta,
    a.fecha,
    a.hora,
    a.importe_obs,
    a.a_cargo_entidad
FROM archivo a
LEFT JOIN asociacion x
    ON x.archivo_id = a.archivo_id
LEFT JOIN recetas r
    ON r.receta_id = x.receta_id
WHERE
    x.asociacion_id IS NULL
    OR r.estado_seguimiento_id = 3;
