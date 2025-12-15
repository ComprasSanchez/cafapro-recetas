import os
from typing import List, Optional, Tuple, TypedDict

import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol


BBox = Tuple[int, int, int, int]


class Detection(TypedDict):
    origin: str
    type: str
    value: str
    bbox: BBox


class FilesOut(TypedDict):
    front_jpg: Optional[str]
    back_jpg: Optional[str]


class ProcessOut(TypedDict):
    headers: List[str]
    troqueles: List[str]
    files: FilesOut


class TiffProcessor:
    # Tipos de códigos que queremos que pyzbar intente detectar
    SYMBOLS = [
        ZBarSymbol.EAN13,
        ZBarSymbol.EAN8,
        ZBarSymbol.CODE128,
        ZBarSymbol.CODE39,
        ZBarSymbol.EAN2,
        ZBarSymbol.EAN5,
    ]

    def __init__(
        self,
        header_types=("CODE128", "CODE39"),
        split_min_ean13: int = 2,
        dedupe_iou: float = 0.70,
    ):
        # Tipos que vamos a considerar "header" (ajustable)
        self.header_types = set(header_types)

        # Si al partir un EAN13 "alto" aparecen al menos N EAN13 válidos,
        # entonces quitamos el EAN13 "full" contenedor (para no devolver 3 cuando son 2)
        self.split_min_ean13 = split_min_ean13

        # Umbral de solapamiento (IoU) para considerar que dos detecciones son el mismo código en el mismo lugar
        self.dedupe_iou = dedupe_iou

    def process(self, tiff_path: str, output_dir: Optional[str] = None) -> ProcessOut:
        # Carga páginas del TIFF (frente/dorso) como imágenes BGR de OpenCV
        pages = self._load_pages(tiff_path)

        if not pages:
            print("No se encontraron páginas en el TIFF.")
            return {
                "headers": [],
                "troqueles": [],
                "files": {"front_jpg": None, "back_jpg": None},
            }

        # Base para el nombre de salida
        base = os.path.splitext(os.path.basename(tiff_path))[0]
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Salida final: solo values (strings)
        headers: List[str] = []
        troqueles: List[str] = []
        files: FilesOut = {"front_jpg": None, "back_jpg": None}

        # Procesamos máximo 2 páginas: 0=frente, 1=dorso (si existe)
        for page_idx, img in enumerate(pages[:2]):
            # 1) Detecta códigos (incluye lógica de split para EAN13 "alto")
            detections = self._detect(img)

            # 2) Extrae SOLO los values de headers + troqueles, ordenados
            self._collect_values(detections, headers, troqueles)

            # 3) Guarda un JPG NORMAL (sin debug aparte), pero con lo encontrado dibujado arriba
            out_path = self._page_out_path(base, page_idx, output_dir)
            annotated = img.copy()
            self._draw_found(annotated, detections)
            cv2.imwrite(out_path, annotated)

            if page_idx == 0:
                files["front_jpg"] = out_path
            else:
                files["back_jpg"] = out_path

        return {"headers": headers, "troqueles": troqueles, "files": files}

    # ---------- Carga ----------
    @staticmethod
    def _load_pages(path: str) -> List[np.ndarray]:
        # 1) Intento con OpenCV multipágina (evita problemas de Pillow con n_frames)
        try:
            ok, pages = cv2.imreadmulti(path, flags=cv2.IMREAD_COLOR)
            if ok and pages:
                return pages
        except cv2.error:
            pass

        # 2) Fallback con Pillow: vamos haciendo seek(i) hasta EOFError (sin usar n_frames)
        pages: List[np.ndarray] = []
        try:
            img = Image.open(path)
            i = 0
            while True:
                try:
                    img.seek(i)
                except EOFError:
                    break
                rgb = img.convert("RGB")
                arr = np.array(rgb)
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                pages.append(bgr)
                i += 1
            img.close()
        except OSError as e:
            print("No se pudo abrir/leer el TIFF:", path, "-", e)

        return pages

    @staticmethod
    def _page_out_path(base: str, page_idx: int, output_dir: Optional[str]) -> str:
        # Convención de nombres: _f = frente, _d = dorso
        suffix = "_f.jpg" if page_idx == 0 else "_d.jpg"
        name = f"{base}{suffix}"
        return os.path.join(output_dir, name) if output_dir else name

    # ---------- Detección ----------
    def _decode(self, img_gray) -> List[Tuple[str, str, int, int, int, int]]:
        # Corre pyzbar sobre una imagen en gris y devuelve (tipo, valor, bbox)
        barcodes = decode(img_gray, symbols=self.SYMBOLS)
        out = []
        for b in barcodes:
            value = b.data.decode("utf-8")
            btype = b.type
            x, y, w, h = b.rect
            out.append((btype, value, x, y, w, h))
        return out

    @staticmethod
    def _iou(a: BBox, b: BBox) -> float:
        # IoU (Intersection over Union): mide cuánto se solapan dos rectángulos.
        # Sirve para deduplicar SOLO cuando es el mismo código en el mismo lugar.
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        inter_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        inter_h = max(0, min(ay + ah, by + bh) - max(ay, by))
        inter = inter_w * inter_h
        if inter == 0:
            return 0.0

        union = aw * ah + bw * bh - inter
        return inter / union

    def _add_result(self, results: List[Detection], origin: str, btype: str, value: str, bbox: BBox) -> None:
        # Evita duplicados generados por el split (mismo tipo+valor en el mismo lugar)
        for det in results:
            if det["type"] == btype and det["value"] == value:
                if self._iou(det["bbox"], bbox) > self.dedupe_iou:
                    return
        results.append({"origin": origin, "type": btype, "value": value, "bbox": bbox})

    def _detect(self, img_bgr) -> List[Detection]:
        # 1) Detección completa sobre la página
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        results: List[Detection] = []

        for btype, value, x, y, w, h in self._decode(gray):
            self._add_result(results, "full", btype, value, (x, y, w, h))

        # 2) Si un EAN13 es "alto" (h > w), lo partimos en top/bottom:
        #    En algunos casos vienen 2 troqueles apilados y el full los confunde como 1.
        to_remove: List[Detection] = []

        for det in list(results):
            if det["type"] != "EAN13" or len(det["value"]) != 13:
                continue

            x, y, w, h = det["bbox"]
            if h < w:
                continue  # no es alto -> no conviene split

            region = gray[y:y + h, x:x + w]
            rh, _ = region.shape
            half_h = rh // 2

            zones = [
                ("split_top", region[:half_h, :], 0, 0),
                ("split_bottom", region[half_h:, :], 0, half_h),
            ]

            split_ean13 = 0
            for origin, sub_img, x_off, y_off in zones:
                for t2, v2, sx, sy, sw, sh in self._decode(sub_img):
                    if t2 == "EAN13" and len(v2) == 13:
                        split_ean13 += 1
                    self._add_result(results, origin, t2, v2, (x + x_off + sx, y + y_off + sy, sw, sh))

            # Si el split encontró los 2 EAN13, entonces el "full" era solo un contenedor.
            # Lo removemos para no devolver 3 resultados (full+top+bottom).
            if split_ean13 >= self.split_min_ean13:
                to_remove.append(det)

        for det in to_remove:
            if det in results:
                results.remove(det)

        return results

    # ---------- Extracción de salida ----------
    def _collect_values(self, detections: List[Detection], headers: List[str], troqueles: List[str]) -> None:
        # Orden estable: de arriba hacia abajo, y de izquierda a derecha
        ordered = sorted(detections, key=lambda _it: (_it["bbox"][1], _it["bbox"][0]))

        # Guardamos solo los values (no el objeto completo)
        for it in ordered:
            t = it["type"]
            v = it["value"]

            if t in self.header_types:
                headers.append(v)

            # Troqueles: EAN13 de 13 dígitos (se permiten repetidos)
            if t == "EAN13" and len(v) == 13:
                troqueles.append(v)

    # ---------- Dibujo (solo headers + troqueles) ----------
    def _draw_found(self, img_bgr, detections: List[Detection]) -> None:
        # Dibuja en el JPG normal:
        # - headers en azul
        # - troqueles EAN13 en verde
        for it in detections:
            t = it["type"]
            v = it["value"]

            is_header = t in self.header_types
            is_troquel = (t == "EAN13" and len(v) == 13)
            if not (is_header or is_troquel):
                continue

            x, y, w, h = it["bbox"]
            color = (255, 0, 0) if is_header else (0, 181, 26)

            cv2.rectangle(img_bgr, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                img_bgr,
                f"{t}:{v}",
                (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                color,
                2,
            )