CREATE OR REPLACE VIEW vw_archivo_receta_debitos AS
SELECT
    rc.numero AS recepcion_numero,
    r.receta_id,
    r.recepcion_id,
    a.fecha,
    a.hora,
    a.orden_lote,
    a.nro_receta,
    a.importe_obs,
    a.a_cargo_entidad,
    md.descripcion AS descripcion_debito,
    r.estado_seguimiento_id,
    es.descripcion AS estado_seguimiento,
    d.detalle,
    r.creado_en
FROM archivo a
JOIN asociacion x
  ON x.archivo_id = a.archivo_id
 AND x.vigente IS TRUE
JOIN recetas r
  ON r.receta_id = x.receta_id
JOIN recepcion rc
  ON rc.recepcion_id = r.recepcion_id
JOIN debitos d
  ON d.receta_id = r.receta_id
JOIN motivo_debito md
  ON md.motivo_debito_id = d.motivo_debito_id
LEFT JOIN estado_seguimiento es
  ON es.estado_seguimiento_id = r.estado_seguimiento_id;





