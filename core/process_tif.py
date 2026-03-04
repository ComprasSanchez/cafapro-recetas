from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, TypedDict, Literal

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
            return pages

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

        H, W = page_bgr.shape[:2]

        roi = page_bgr[int(H * 0.05):int(H * 0.28), :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # intento rápido con ZBAR
        hits = zbar_decode(
            gray,
            symbols=[ZBarSymbol.CODE128, ZBarSymbol.CODE39]
        )

        if hits:

            for b in hits:
                value = b.data.decode("utf-8")

                x, y, w, h = b.rect

                headers.append(value)

                dets.append({
                    "page_idx": page_idx,
                    "type": b.type,
                    "value": value,
                    "bbox": (x, y + int(H * 0.05), w, h),
                    "source": "zbar"
                })

            return headers, dets

        # --------------------
        # OCR fallback
        # --------------------

        results = EASY_OCR_READER.readtext(
            gray,
            detail=0,
            paragraph=False,
            allowlist="0123456789"
        )

        numbers = []

        for text in results:
            numbers.extend(re.findall(r"\d+", text))

        ean = None
        imed = ""

        for n in numbers:

            if len(n) == 13 and not ean:
                ean = n
                continue

            imed += n

        if ean:
            headers.append(ean)

        if len(imed) >= 20:
            headers.append(imed[:20])

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

        hits = zbar_decode(
            gray,
            symbols=[ZBarSymbol.EAN13]
        )

        for b in hits:

            value = b.data.decode("utf-8")

            if not (value.isdigit() and len(value) == 13):
                continue

            x,y,w,h = b.rect

            troqueles.append(value)

            dets.append({
                "page_idx": page_idx,
                "type": "EAN13",
                "value": value,
                "bbox": (x,y,w,h),
                "source": "zbar",
                "masked": False
            })

        return troqueles, dets


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

                cv2.rectangle(canvas,(x,y),(x+w,y+h),self.C_HEADER,2)

                cv2.putText(
                    canvas,
                    d["value"],
                    (x,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    self.C_HEADER,
                    2
                )

            # TROQUELES

            for d in scan.troquel_detections:

                if d["page_idx"] != page_idx:
                    continue

                x,y,w,h = d["bbox"]

                val = d["value"]

                estado = get_estado(val)

                color = self.C_V if estado == "V" else (self.C_R if estado == "R" else self.C_A)

                cv2.rectangle(canvas,(x,y),(x+w,y+h),color,2)

                cv2.putText(
                    canvas,
                    f"{val} [{estado}]",
                    (x,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

            ok, buf = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpg_quality])

            if not ok:
                continue

            if page_idx == 0:
                out["front_bytes"] = buf.tobytes()
            else:
                out["back_bytes"] = buf.tobytes()

        return out


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