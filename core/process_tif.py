from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Literal

import cv2
import easyocr
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol


warnings.filterwarnings("ignore")

BBox = Tuple[int, int, int, int]
TroquelEstado = Literal["V", "A", "R"]

# OCR inicializado una sola vez
EASY_OCR_READER = easyocr.Reader(['en'], gpu=False)


class HeaderDet(TypedDict):
    page_idx: int
    type: str
    value: str
    bbox: BBox
    source: str


class TroquelDet(TypedDict):
    page_idx: int
    type: str
    value: str
    bbox: BBox
    source: str
    masked: bool


class FilesOut(TypedDict):
    front_bytes: Optional[bytes]
    back_bytes: Optional[bytes]


@dataclass(frozen=True)
class ScanOut:
    base_name: str
    headers: List[str]
    troqueles: List[str]
    header_detections: List[HeaderDet]
    troquel_detections: List[TroquelDet]


# ============================================================
# SCANNER
# ============================================================

class TiffZBarMaskedScanner:

    def __init__(
        self,
        *,
        max_pages: int = 2,
    ):
        self.max_pages = max_pages

    # --------------------------------------------------------
    # TIFF LOADER
    # --------------------------------------------------------

    @staticmethod
    def load_pages_bgr(tiff_path: str) -> List[np.ndarray]:

        ok, pages = cv2.imreadmulti(tiff_path, flags=cv2.IMREAD_COLOR)

        if ok and pages:
            return list(pages)

        pages = []
        img = Image.open(tiff_path)

        i = 0
        while True:
            try:
                img.seek(i)
            except EOFError:
                break

            rgb = img.convert("RGB")
            arr = np.array(rgb)
            pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
            i += 1

        img.close()

        return pages

    # --------------------------------------------------------
    # MAIN PROCESS
    # --------------------------------------------------------

    def process_pages(self, pages: List[np.ndarray], base_name: str) -> ScanOut:

        headers = []
        troqueles = []
        header_dets = []
        troquel_dets = []

        for page_idx, page_bgr in enumerate(pages[: self.max_pages]):

            # HEADERS SOLO EN PRIMERA PAGINA
            if page_idx == 0:

                h_vals, h_dets = self._scan_page_headers(
                    page_bgr,
                    page_idx=page_idx
                )

                headers.extend(h_vals)
                header_dets.extend(h_dets)

            t_vals, t_dets = self._scan_page_troqueles(
                page_bgr,
                page_idx=page_idx
            )

            troqueles.extend(t_vals)
            troquel_dets.extend(t_dets)

        return ScanOut(
            base_name=base_name,
            headers=headers,
            troqueles=troqueles,
            header_detections=header_dets,
            troquel_detections=troquel_dets,
        )

    # --------------------------------------------------------
    # HEADER DETECTION
    # --------------------------------------------------------

    def _scan_page_headers(self, page_bgr: np.ndarray, *, page_idx: int):

        headers = []
        dets = []

        H, _W = page_bgr.shape[:2]

        roi = page_bgr[int(H * 0.05):int(H * 0.28), :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # --------------------
        # OCR only (headers)
        # --------------------

        results = EASY_OCR_READER.readtext(
            gray,
            detail=1,
            paragraph=False,
            allowlist="0123456789"
        )

        for item in results:
            row: Any = item
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue

            bbox_pts = row[0]
            text = row[1]
            raw_txt = self._norm_ocr_text(text)
            if not raw_txt or not raw_txt.isdigit():
                continue

            rect = self._ocr_bbox_to_rect(bbox_pts)
            if rect is None:
                continue

            x, y, w, hh = rect
            bbox = (x, y + int(H * 0.05), w, hh)
            headers.append(raw_txt)
            dets.append({
                "page_idx": page_idx,
                "type": "OCR",
                "value": raw_txt,
                "bbox": bbox,
                "source": "ocr",
            })

        return headers, dets

    # --------------------------------------------------------
    # TROQUEL DETECTION
    # --------------------------------------------------------

    def _scan_page_troqueles(
        self,
        page_bgr: np.ndarray,
        *,
        page_idx: int
    ):

        troqueles = []
        dets = []

        gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)

        symbols = [ZBarSymbol.EAN13]
        upca = getattr(ZBarSymbol, "UPCA", None)
        if upca is not None:
            symbols.append(upca)

        hits = zbar_decode(gray, symbols=symbols)

        seen: set[tuple[str, int, int]] = set()
        bucket = 16

        for b in hits:
            try:
                value = b.data.decode("utf-8").strip()
            except Exception:
                continue

            value = "".join(ch for ch in value if ch.isdigit())

            if not (value.isdigit() and len(value) in (12, 13)):
                continue

            x, y, w, hh = b.rect
            cx = int((int(x) + int(w) / 2) // bucket)
            cy = int((int(y) + int(hh) / 2) // bucket)
            key = (value, cx, cy)

            if key in seen:
                continue
            seen.add(key)

            troqueles.append(value)

            dets.append({
                "page_idx": page_idx,
                "type": str(getattr(b, "type", "EAN13")),
                "value": value,
                "bbox": (int(x), int(y), int(w), int(hh)),
                "source": "zbar",
                "masked": False,
            })

        return troqueles, dets

    @staticmethod
    def _ocr_bbox_to_rect(bbox_pts) -> Optional[BBox]:
        if not bbox_pts:
            return None

        xs: List[int] = []
        ys: List[int] = []

        for p in bbox_pts:
            if not p or len(p) < 2:
                continue
            try:
                xs.append(int(float(p[0])))
                ys.append(int(float(p[1])))
            except Exception:
                continue

        if not xs or not ys:
            return None

        x = min(xs)
        y = min(ys)
        w = max(1, max(xs) - x)
        h = max(1, max(ys) - y)
        return x, y, w, h

    @staticmethod
    def _norm_ocr_text(text: Any) -> str:
        raw = f"{text}".strip()
        if not raw:
            return ""
        return "".join(ch for ch in raw if not ch.isspace())


# ============================================================
# RENDERER
# ============================================================

class TiffScanRenderer:

    def __init__(self, *, jpg_quality: int = 85):

        self.jpg_quality = jpg_quality

        self.C_HEADER = (255,0,0)
        self.C_V = (0,181,26)
        self.C_A = (0,255,255)
        self.C_R = (0,0,255)

    def render_bytes(
        self,
        tiff_path: str,
        scan: ScanOut,
        *,
        estado_por_codebar: Optional[Dict[str, TroquelEstado]] = None,
        estado_resolver: Optional[Callable[[str], TroquelEstado]] = None,
        pages: Optional[List[np.ndarray]] = None,
    ) -> FilesOut:

        if pages is None:
            pages = TiffZBarMaskedScanner.load_pages_bgr(tiff_path)

        out: FilesOut = {
            "front_bytes": None,
            "back_bytes": None
        }

        def get_estado(codebar: str) -> TroquelEstado:

            if estado_por_codebar and codebar in estado_por_codebar:
                return estado_por_codebar[codebar]

            if estado_resolver:
                return estado_resolver(codebar)

            return "A"

        for page_idx, img in enumerate(pages[:2]):

            canvas = img.copy()

            # HEADERS

            for d in scan.header_detections:

                if d["page_idx"] != page_idx:
                    continue

                x,y,w,h = d["bbox"]
                self._draw_center_line(
                    canvas,
                    (x, y, w, h),
                    self.C_HEADER,
                    min_thickness=1,
                    scale=0.05,
                    y_factor=-0.55,
                )

            # TROQUELES

            for d in scan.troquel_detections:

                if d["page_idx"] != page_idx:
                    continue

                x,y,w,h = d["bbox"]

                val = d["value"]

                estado = get_estado(val)

                color = self.C_V if estado == "V" else (self.C_R if estado == "R" else self.C_A)
                self._draw_center_line(canvas, (x, y, w, h), color, min_thickness=1, scale=0.08)

            ok, buf = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpg_quality])

            if not ok:
                continue

            if page_idx == 0:
                out["front_bytes"] = buf.tobytes()
            else:
                out["back_bytes"] = buf.tobytes()

        return out

    @staticmethod
    def _draw_center_line(
        canvas: np.ndarray,
        bbox: BBox,
        color: Tuple[int, int, int],
        *,
        min_thickness: int = 2,
        scale: float = 0.12,
        y_factor: float = 0.5,
    ) -> None:
        h_img, w_img = canvas.shape[:2]

        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            return

        x1 = max(0, min(w_img - 1, int(x)))
        x2 = max(0, min(w_img - 1, int(x + w)))
        if x2 <= x1:
            x2 = min(w_img - 1, x1 + 1)

        y_mid = max(0, min(h_img - 1, int(y + (h * float(y_factor)))))
        thickness = max(int(min_thickness), int(round(h * float(scale))))

        cv2.line(canvas, (x1, y_mid), (x2, y_mid), color, thickness)


# ============================================================
# FACADE
# ============================================================

class TiffProcessor:

    def __init__(self):

        self._scanner = TiffZBarMaskedScanner()

        self._renderer = TiffScanRenderer()

    def scan(self, tiff_path: str) -> ScanOut:

        pages = TiffZBarMaskedScanner.load_pages_bgr(tiff_path)

        base = os.path.splitext(os.path.basename(tiff_path))[0]

        return self._scanner.process_pages(pages, base)

    def scan_with_pages(self, tiff_path: str):

        pages = TiffZBarMaskedScanner.load_pages_bgr(tiff_path)

        base = os.path.splitext(os.path.basename(tiff_path))[0]

        scan = self._scanner.process_pages(pages, base)

        return scan, pages

    def render_bytes(
        self,
        *,
        tiff_path: str,
        scan: ScanOut,
        estado_por_codebar: Optional[Dict[str, TroquelEstado]] = None,
        estado_resolver: Optional[Callable[[str], TroquelEstado]] = None,
        pages: Optional[List[np.ndarray]] = None,
    ) -> FilesOut:

        return self._renderer.render_bytes(
            tiff_path,
            scan,
            estado_por_codebar=estado_por_codebar,
            estado_resolver=estado_resolver,
            pages=pages
        )
