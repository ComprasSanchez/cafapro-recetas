import os
import csv
from config.config_manager import ConfigManager


class ImedCvsHandler(object):
    def __init__(self, parent=None):
        self._config = ConfigManager()

        # Intentar cargar la config
        config_loaded = self._config.load()

        # Si no existe, pedir carpetas (asegurate que ask_for_folders guarde "imed_folder")
        if not config_loaded:
            self._config.ask_for_folders(parent=parent)

        self.imed_folder = self._config.get("imed_folder")

        if not self.imed_folder:
            raise ValueError(
                "imed_folder no esta configurado. "
                "Vuelva a ejecutar la configuración."
            )

    # ─────────────────────────────────────────────
    # LECTURA DEL CSV IMED
    # ─────────────────────────────────────────────
    def read_cvs(self, path: str):
        recetas_por_ref = {}    # key: nro referencia → value: dict con datos receta
        detalles_por_ref = {}   # key: nro referencia → value: lista de detalles

        # newline="" es recomendado para csv en Windows
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=";")

            encabezado = None
            lineas_restantes = []  # donde voy a guardar lo que viene después

            for fila in reader:
                if not fila or all(campo == "" for campo in fila):
                    continue

                if fila[0].startswith("DETALLE_"):
                    # ya estamos en la sección de detalles → guardo esta y lo que sigue
                    lineas_restantes.append(fila)
                    break

                if encabezado is None:
                    encabezado = fila  # primera fila con nombres de columnas
                    continue

                # fila con datos de receta
                receta = dict(zip(encabezado, fila))
                nro_ref = receta.get("Nro Referencia")

                # print(receta)  # ← si lo querés solo para debug, lo podés dejar comentado.

                if not nro_ref:
                    # si no tiene nro referencia, la salteamos
                    continue

                recetas_por_ref[nro_ref] = receta

            # también guardo el resto de líneas (todos los detalles)
            for fila in reader:
                lineas_restantes.append(fila)

        # 2) Procesar la parte de DETALLES usando las líneas restantes
        current_ref = None
        for fila in lineas_restantes:
            if not fila or all(campo == "" for campo in fila):
                continue

            # Línea tipo DETALLE_20251202073430607100
            if fila[0].startswith("DETALLE_"):
                current_ref = fila[0].replace("DETALLE_", "").strip()
                if current_ref not in detalles_por_ref:
                    detalles_por_ref[current_ref] = []
                continue

            if current_ref is None:
                continue

            # Acá adapto las posiciones según tu formato
            detalle = {
                "code":          fila[0] if len(fila) > 0 else None,
                "name":          fila[1] if len(fila) > 1 else None,
                "description":   fila[2] if len(fila) > 2 else None,
                "estatus":       fila[3] if len(fila) > 3 else None,
                "number_aut":    fila[4] if len(fila) > 4 else None,
                "quantity":      fila[5] if len(fila) > 5 else None,
                "amount_general": fila[6] if len(fila) > 6 else None,
                "amount_obs":    fila[7] if len(fila) > 7 else None,
                "discount":      fila[8] if len(fila) > 8 else None,
            }

            detalles_por_ref[current_ref].append(detalle)

        return recetas_por_ref, detalles_por_ref

    # ─────────────────────────────────────────────
    # ARMAR PATH DEL CSV A PARTIR DE IMED + FECHA
    # ─────────────────────────────────────────────
    def get_path_cvs(self, imed: str, date: str) -> str:
        cleaned_date = date.strip()

        if cleaned_date.isdigit() and len(cleaned_date) == 8:
            # Ya está en formato YYYYMMDD
            yyyymmdd = cleaned_date
        else:
            # Intentamos DD/MM/YYYY -> YYYYMMDD
            try:
                dd, mm, yyyy = cleaned_date.split("/")
                yyyymmdd = f"{yyyy}{mm}{dd}"
            except ValueError:
                raise ValueError(
                    f"Formato de fecha inválido: '{date}'. Use 'YYYYMMDD' o 'DD/MM/YYYY'."
                )

        filename = f"a_{imed}_{yyyymmdd}.csv"
        raw_path = os.path.join(self.imed_folder, filename)
        full_path = os.path.normpath(raw_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f"No se encontró el archivo IMED: {full_path}"
            )

        return full_path

    # ─────────────────────────────────────────────
    # ATAJO: LEER POR IMED + FECHA
    # ─────────────────────────────────────────────
    def read_cvs_by_imed_and_date(self, imed: str, date: str):
        path = self.get_path_cvs(imed, date)
        return self.read_cvs(path)


