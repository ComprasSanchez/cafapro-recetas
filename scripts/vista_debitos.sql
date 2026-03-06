DROP VIEW IF EXISTS vw_archivo_receta_debitos;

CREATE OR REPLACE VIEW vw_archivo_receta_debitos AS
SELECT
    rc.numero AS recepcion_numero,
    pr.nombre AS prestador_nombre,

    r.receta_id,
    r.recepcion_id,

    a.fecha,
    a.hora,
    a.orden_lote,
    r.nro_receta,

    a.importe_obs,
    a.a_cargo_entidad,

    md.descripcion AS descripcion_debito,

    r.estado_seguimiento_id,
    es.descripcion AS estado_seguimiento,

    ven.descripcion AS vendedor_nombre,
    u.username AS auditor_nombre,

    d.detalle,
    r.creado_en

FROM debitos d

JOIN recetas r
  ON r.receta_id = d.receta_id

JOIN recepcion rc
  ON rc.recepcion_id = r.recepcion_id

JOIN prestador pr
  ON pr.prestador_id = rc.prestador_id

JOIN motivo_debito md
  ON md.motivo_debito_id = d.motivo_debito_id

LEFT JOIN estado_seguimiento es
  ON es.estado_seguimiento_id = r.estado_seguimiento_id

LEFT JOIN vendedores ven
  ON ven.vendedor_id = r.vendedor_id

LEFT JOIN usuarios u
  ON u.usuario_id = r.usuario_id

LEFT JOIN asociacion x
  ON x.receta_id = r.receta_id
 AND x.vigente IS TRUE

LEFT JOIN archivo a
  ON a.archivo_id = x.archivo_id;

