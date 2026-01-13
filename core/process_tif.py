from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, TypedDict, Literal

import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol


BBox = Tuple[int, int, int, int]
TroquelEstado = Literal["V", "A", "R"]  # Verde / Amarillo / Rojo


class Detection(TypedDict):
    origin: str
    type: str
    value: str
    bbox: BBox


class FilesOut(TypedDict):
    front_jpg: Optional[str]
    back_jpg: Optional[str]


@dataclass(frozen=True)
class PageScan:
    page_idx: int
    detections: List[Detection]


@dataclass(frozen=True)
class ScanOut:
    headers: List[str]
    troqueles: List[str]
    pages: List[PageScan]  # detecciones por página (para render)
    base_name: str         # nombre base del tif (sin extensión)


# =========================
# SCANNER (solo detecta + extrae values)
# =========================
class TiffScanner:
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
        self.header_types = set(header_types)
        self.split_min_ean13 = split_min_ean13
        self.dedupe_iou = dedupe_iou

    def scan(self, tiff_path: str) -> ScanOut:
        pages_img = self._load_pages(tiff_path)

        base = os.path.splitext(os.path.basename(tiff_path))[0]

        if not pages_img:
            return ScanOut(headers=[], troqueles=[], pages=[], base_name=base)

        headers: List[str] = []
        troqueles: List[str] = []
        pages: List[PageScan] = []

        for page_idx, img in enumerate(pages_img[:2]):
            detections = self._detect(img)
            self._collect_values(detections, headers, troqueles)
            pages.append(PageScan(page_idx=page_idx, detections=detections))

        return ScanOut(headers=headers, troqueles=troqueles, pages=pages, base_name=base)

    # ---------- Carga ----------
    @staticmethod
    def _load_pages(path: str) -> List[np.ndarray]:
        try:
            ok, pages = cv2.imreadmulti(path, flags=cv2.IMREAD_COLOR)
            if ok and pages:
                return pages
        except cv2.error:
            pass

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
        except OSError:
            pass

        return pages

    # ---------- Detección ----------
    def _decode(self, img_gray) -> List[Tuple[str, str, int, int, int, int]]:
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
        for det in results:
            if det["type"] == btype and det["value"] == value:
                if self._iou(det["bbox"], bbox) > self.dedupe_iou:
                    return
        results.append({"origin": origin, "type": btype, "value": value, "bbox": bbox})

    def _detect(self, img_bgr) -> List[Detection]:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        results: List[Detection] = []

        # 1) detección completa
        for btype, value, x, y, w, h in self._decode(gray):
            self._add_result(results, "full", btype, value, (x, y, w, h))

        to_remove: List[Detection] = []
        pad = 18

        H, W = gray.shape[:2]

        for det in list(results):
            if det["origin"] != "full":
                continue

            x, y, w, h = det["bbox"]
            if w <= 0 or h <= 0:
                continue

            # ✅ criterio 67% sin decimales
            is_tallish = (3 * h > 2 * w)  # h/w > 0.67
            is_widish = (3 * w > 2 * h)  # w/h > 0.67 (por si el contenedor es horizontal)
            if not (is_tallish or is_widish):
                continue

            # recorte con padding
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(W, x + w + pad)
            y1 = min(H, y + h + pad)
            region = gray[y0:y1, x0:x1]
            if region.size == 0:
                continue

            rh, rw = region.shape[:2]

            # ✅ elegimos split por el bbox original (no por region)
            if is_tallish:
                half_h = rh // 2
                zones = [
                    ("split_top", region[:half_h, :], 0, 0),
                    ("split_bottom", region[half_h:, :], 0, half_h),
                ]
            else:
                half_w = rw // 2
                zones = [
                    ("split_left", region[:, :half_w], 0, 0),
                    ("split_right", region[:, half_w:], half_w, 0),
                ]

            split_ean13 = 0

            for origin, sub_img, x_off, y_off in zones:
                for t2, v2, sx, sy, sw, sh in self._decode(sub_img):
                    v2 = (v2 or "").strip()

                    if t2 == "EAN13" and len(v2) == 13 and v2.isdigit():
                        split_ean13 += 1

                    self._add_result(
                        results,
                        origin,
                        t2,
                        v2,
                        (x0 + x_off + sx, y0 + y_off + sy, sw, sh),
                    )

            if split_ean13 >= self.split_min_ean13:
                to_remove.append(det)

        for det in to_remove:
            if det in results:
                results.remove(det)

        return results

    # ---------- extracción ----------
    def _collect_values(self, detections: List[Detection], headers: List[str], troqueles: List[str]) -> None:
        ordered = sorted(detections, key=lambda _it: (_it["bbox"][1], _it["bbox"][0]))

        for it in ordered:
            t = it["type"]
            v = it["value"]

            if t in self.header_types:
                headers.append(v)

            if t == "EAN13" and len(v) == 13:
                troqueles.append(v)


# =========================
# RENDERER (solo dibuja + escribe jpg)
# =========================
class TiffRenderer:
    def __init__(self, header_types=("CODE128", "CODE39")):
        self.header_types = set(header_types)

    @staticmethod
    def _page_out_path(base: str, page_idx: int, output_dir: Optional[str]) -> str:
        suffix = "_f.jpg" if page_idx == 0 else "_d.jpg"
        name = f"{base}{suffix}"
        return os.path.join(output_dir, name) if output_dir else name

    def render(
        self,
        tiff_path: str,
        scan: ScanOut,
        output_dir: Optional[str],
        estado_por_codebar: Dict[str, TroquelEstado] | None = None,
        estado_resolver: Callable[[str], TroquelEstado] | None = None,
    ) -> FilesOut:
        """
        Dibuja y guarda:
        - headers: azul
        - troqueles: según estado
            V => verde
            A => amarillo
            R => rojo

        estado_por_codebar: dict {EAN13: "V"|"A"|"R"}
        estado_resolver: función(codebar)->estado (si querés lazy)
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        pages_img = TiffScanner._load_pages(tiff_path)
        files: FilesOut = {"front_jpg": None, "back_jpg": None}

        if not pages_img or not scan.pages:
            return files

        for page_idx, img in enumerate(pages_img[:2]):
            # detecciones de esa página (si no hay, lista vacía)
            page_scan = next((p for p in scan.pages if p.page_idx == page_idx), None)
            detections = page_scan.detections if page_scan else []

            annotated = img.copy()
            self._draw_found(
                annotated,
                detections,
                estado_por_codebar=estado_por_codebar,
                estado_resolver=estado_resolver,
            )

            out_path = self._page_out_path(scan.base_name, page_idx, output_dir)
            cv2.imwrite(out_path, annotated)

            if page_idx == 0:
                files["front_jpg"] = out_path
            else:
                files["back_jpg"] = out_path

        return files

    def _draw_found(
        self,
        img_bgr,
        detections: List[Detection],
        estado_por_codebar: Dict[str, TroquelEstado] | None,
        estado_resolver: Callable[[str], TroquelEstado] | None,
    ) -> None:
        # BGR
        COLOR_HEADER = (255, 0, 0)      # azul
        COLOR_V = (0, 181, 26)          # verde
        COLOR_A = (0, 255, 255)         # amarillo
        COLOR_R = (0, 0, 255)           # rojo

        def get_estado(codebar: str) -> TroquelEstado:
            if estado_por_codebar and codebar in estado_por_codebar:
                return estado_por_codebar[codebar]
            if estado_resolver:
                return estado_resolver(codebar)
            return "A"  # default: amarillo si no sabemos

        ordered = sorted(detections, key=lambda _it: (_it["bbox"][1], _it["bbox"][0]))

        for it in ordered:
            t = it["type"]
            v = it["value"]

            is_header = t in self.header_types
            is_troquel = (t == "EAN13" and len(v) == 13)
            if not (is_header or is_troquel):
                continue

            x, y, w, h = it["bbox"]

            if is_header:
                color = COLOR_HEADER
                label = f"{t}:{v}"
            else:
                estado = get_estado(v)
                if estado == "V":
                    color = COLOR_V
                elif estado == "R":
                    color = COLOR_R
                else:
                    color = COLOR_A
                label = f"EAN13:{v} [{estado}]"

            cv2.rectangle(img_bgr, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                img_bgr,
                label,
                (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                color,
                2,
            )


# =========================
# FACHADA (lo que usa el service)
# =========================
class TiffProcessor:
    """
    Wrapper para usar:
      - scan()  => solo detección/extracción
      - render() => solo dibujo
    """
    def __init__(
        self,
        header_types=("CODE128", "CODE39"),
        split_min_ean13: int = 2,
        dedupe_iou: float = 0.70,
    ):
        self.scanner = TiffScanner(
            header_types=header_types,
            split_min_ean13=split_min_ean13,
            dedupe_iou=dedupe_iou,
        )
        self.renderer = TiffRenderer(header_types=header_types)

    def scan(self, tiff_path: str) -> ScanOut:
        return self.scanner.scan(tiff_path)

    def render(
        self,
        tiff_path: str,
        scan: ScanOut,
        output_dir: Optional[str],
        estado_por_codebar: Dict[str, TroquelEstado] | None = None,
        estado_resolver: Callable[[str], TroquelEstado] | None = None,
    ) -> FilesOut:
        return self.renderer.render(
            tiff_path=tiff_path,
            scan=scan,
            output_dir=output_dir,
            estado_por_codebar=estado_por_codebar,
            estado_resolver=estado_resolver,
        )
