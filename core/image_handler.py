import os
import datetime
from config.config_manager import ConfigManager


class ImageHandler:
    """
    Clase encargada de:
      - Cargar (o pedir) la carpeta base de imágenes desde la config.
      - Buscar imágenes .tif según:
          * carpeta de sucursal (name_folder)
          * nombre de la obra social en el archivo (obs)
          * timestamp en el nombre del archivo para sacar la hora
    """

    def __init__(self, parent=None):
        """
        :param parent: Ventana padre de Tkinter (opcional), por si querés
                       que los diálogos de selección cuelguen de una ventana.
        """
        self._config = ConfigManager()

        # 1) Intentamos cargar la configuración desde disco
        config_loaded = self._config.load()

        # 2) Si no existe config.json, se la pedimos al usuario
        if not config_loaded:
            self._config.ask_for_folders(parent=parent)

        # 3) Obtenemos la carpeta base de imágenes
        self.image_folder = self._config.get("image_folder")

        # 4) Validación mínima
        if not self.image_folder:
            raise ValueError(
                "image_folder no está configurado. "
                "Vuelve a ejecutar la configuración."
            )


    def get_images_tif(self, name_folder: str, date: str | None, obs: str):
        target_path = os.path.join(self.image_folder, name_folder)

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"No existe la carpeta: {target_path}")

        obs_lower = obs.lower()
        results = []

        # Convertir fecha del filtro a datetime.date
        filter_date = None
        if date:
            try:
                filter_date = datetime.datetime.strptime(date, "%d/%m/%Y").date()
            except ValueError:
                raise ValueError(f"Formato incorrecto de fecha '{date}'. Use DD/MM/YYYY")

        for file in os.listdir(target_path):
            lower_name = file.lower()

            # Solo .tif
            if not lower_name.endswith(".tif"):
                continue

            # Debe contener la obra social
            if obs_lower not in lower_name:
                continue

            full_path = os.path.join(target_path, file)

            # Obtener fecha de creación/modificación
            ctime = os.path.getctime(full_path)
            file_datetime = datetime.datetime.fromtimestamp(ctime)
            file_date_str = file_datetime.strftime("%d/%m/%Y")

            # Filtrar por fecha REAL si se pasó una fecha
            if filter_date and file_datetime.date() != filter_date:
                continue

            # Extraer la hora desde el nombre (timestamp)
            try:
                after_prefix = file.split("_", 1)[1]
                timestamp_part = after_prefix.split(".", 1)[0]
            except IndexError:
                continue

            if len(timestamp_part) < 14 or not timestamp_part.isdigit():
                continue

            hh = timestamp_part[8:10]
            mm = timestamp_part[10:12]
            ss = timestamp_part[12:14]

            time_str = f"{hh}:{mm}:{ss}"

            results.append(
                {
                    "name": file,
                    "date": file_date_str,  # ← AHORA ES LA FECHA REAL DEL ARCHIVO
                    "time": time_str,
                    "full_path": full_path
                }
            )

        return results

