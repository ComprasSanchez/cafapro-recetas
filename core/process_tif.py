from __future__ import annotations

import os
import time
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Literal

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "2")

import cv2
import easyocr
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol


warnings.filterwarnings("ignore")
cv2.setNumThreads(2)
cv2.ocl.setUseOpenCL(False)

try:
    import torch

    torch.set_num_threads(2)
    if hasattr(torch, "set_num_interop_threads"):
        torch.set_num_interop_threads(2)
except Exception:
    pass

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
    scan_load_seconds: float = 0.0
    scan_ocr_seconds: float = 0.0
    scan_zbar_seconds: float = 0.0


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
    def load_pages_bgr(tiff_path: str, *, max_pages: int | None = None) -> List[np.ndarray]:
        pages: List[np.ndarray] = []
        max_pages_int = int(max_pages) if max_pages is not None else None

        try:
            img = Image.open(tiff_path)
            i = 0
            while True:
                if max_pages_int is not None and i >= max_pages_int:
                    break

                try:
                    img.seek(i)
                except EOFError:
                    break

                rgb = img.convert("RGB")
                arr = np.array(rgb)
                pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
                i += 1

            img.close()
            if pages:
                return pages
        except Exception:
            pass

        ok, pages_cv = cv2.imreadmulti(tiff_path, flags=cv2.IMREAD_COLOR)
        if not ok or not pages_cv:
            return []

        if max_pages_int is not None:
            return list(pages_cv[:max_pages_int])
        return list(pages_cv)

    # --------------------------------------------------------
    # MAIN PROCESS
    # --------------------------------------------------------

    def process_pages(
        self,
        pages: List[np.ndarray],
        base_name: str,
        *,
        load_pages_seconds: float = 0.0,
    ) -> ScanOut:

        headers = []
        troqueles = []
        header_dets = []
        troquel_dets = []
        ocr_seconds = 0.0
        zbar_seconds = 0.0

        for page_idx, page_bgr in enumerate(pages[: self.max_pages]):

            # HEADERS SOLO EN PRIMERA PAGINA
            if page_idx == 0:
                h_vals, h_dets, h_ocr_seconds, h_zbar_seconds = self._scan_page_headers(
                    page_bgr,
                    page_idx=page_idx
                )
                ocr_seconds += h_ocr_seconds
                zbar_seconds += h_zbar_seconds

                headers.extend(h_vals)
                header_dets.extend(h_dets)

            zbar_started_at = time.perf_counter()
            t_vals, t_dets = self._scan_page_troqueles(
                page_bgr,
                page_idx=page_idx
            )
            zbar_seconds += max(0.0, time.perf_counter() - zbar_started_at)

            troqueles.extend(t_vals)
            troquel_dets.extend(t_dets)

        return ScanOut(
            base_name=base_name,
            headers=headers,
            troqueles=troqueles,
            header_detections=header_dets,
            troquel_detections=troquel_dets,
            scan_load_seconds=float(load_pages_seconds),
            scan_ocr_seconds=ocr_seconds,
            scan_zbar_seconds=zbar_seconds,
        )

    # --------------------------------------------------------
    # HEADER DETECTION
    # --------------------------------------------------------

    def _scan_page_headers(self, page_bgr: np.ndarray, *, page_idx: int):

        headers = []
        dets = []
        ocr_seconds = 0.0
        zbar_seconds = 0.0

        H, _W = page_bgr.shape[:2]

        roi_top = int(H * 0.05)
        roi_bottom = int(H * 0.24)
        roi = page_bgr[roi_top:roi_bottom, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Header first con zbar (sin rotaciones)
        zbar_started_at = time.perf_counter()
        zbar_headers, zbar_dets = self._scan_header_with_zbar(
            gray,
            page_idx=page_idx,
            roi_top=roi_top,
        )
        zbar_seconds += max(0.0, time.perf_counter() - zbar_started_at)

        if zbar_headers:
            return zbar_headers, zbar_dets, ocr_seconds, zbar_seconds

        # fast-path: OCR liviano para extraer solo texto de headers
        ocr_started_at = time.perf_counter()
        gray_fast = gray
        if gray_fast.shape[1] > 1400:
            gray_fast = cv2.resize(
                gray_fast,
                None,
                fx=0.75,
                fy=0.75,
                interpolation=cv2.INTER_AREA,
            )

        fast_results = EASY_OCR_READER.readtext(
            gray_fast,
            detail=0,
            paragraph=False,
            allowlist="0123456789",
        )

        fast_headers: list[str] = []
        seen_fast: set[str] = set()
        for text in fast_results:
            raw_txt = self._norm_ocr_text(text)
            if not raw_txt or not raw_txt.isdigit() or len(raw_txt) < 6:
                continue
            if raw_txt in seen_fast:
                continue
            seen_fast.add(raw_txt)
            fast_headers.append(raw_txt)

        if fast_headers:
            ocr_seconds += max(0.0, time.perf_counter() - ocr_started_at)
            return fast_headers, dets, ocr_seconds, zbar_seconds

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
            bbox = (x, y + roi_top, w, hh)
            headers.append(raw_txt)
            dets.append({
                "page_idx": page_idx,
                "type": "OCR",
                "value": raw_txt,
                "bbox": bbox,
                "source": "ocr",
            })

        ocr_seconds += max(0.0, time.perf_counter() - ocr_started_at)
        return headers, dets, ocr_seconds, zbar_seconds

    def _scan_header_with_zbar(
        self,
        gray_roi: np.ndarray,
        *,
        page_idx: int,
        roi_top: int,
    ) -> tuple[list[str], list[HeaderDet]]:
        symbols = [ZBarSymbol.EAN13]

        upca = getattr(ZBarSymbol, "UPCA", None)
        if upca is not None:
            symbols.append(upca)

        code128 = getattr(ZBarSymbol, "CODE128", None)
        if code128 is not None:
            symbols.append(code128)

        headers: list[str] = []
        dets: list[HeaderDet] = []
        seen_values: set[str] = set()

        def _decode_attempt(
            img: np.ndarray,
            *,
            map_rect: Callable[[tuple[int, int, int, int]], tuple[int, int, int, int]],
            source: str,
        ) -> None:
            nonlocal headers, dets

            hits = zbar_decode(img, symbols=symbols)
            if not hits:
                return

            for b in hits:
                try:
                    raw = b.data.decode("utf-8").strip()
                except Exception:
                    continue

                value = "".join(ch for ch in raw if ch.isdigit())
                if not self._is_valid_header_candidate(value):
                    continue
                if value in seen_values:
                    continue

                seen_values.add(value)
                headers.append(value)

                x, y, w, hh = map_rect((int(b.rect[0]), int(b.rect[1]), int(b.rect[2]), int(b.rect[3])))
                dets.append({
                    "page_idx": page_idx,
                    "type": str(getattr(b, "type", "BARCODE")),
                    "value": value,
                    "bbox": (x, y + int(roi_top), max(1, w), max(1, hh)),
                    "source": source,
                })

        # Fase 1: sin deskew
        _decode_attempt(
            gray_roi,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        if gray_roi.shape[1] > 1400:
            resized = cv2.resize(
                gray_roi,
                None,
                fx=0.8,
                fy=0.8,
                interpolation=cv2.INTER_AREA,
            )
            scale_x = float(gray_roi.shape[1]) / float(resized.shape[1])
            scale_y = float(gray_roi.shape[0]) / float(resized.shape[0])

            _decode_attempt(
                resized,
                map_rect=lambda r, sx=scale_x, sy=scale_y: self._scale_rect(r, sx=sx, sy=sy),
                source="zbar_header",
            )
            if headers:
                return headers, dets

        eq = cv2.equalizeHist(gray_roi)
        _decode_attempt(
            eq,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray_roi)
        _decode_attempt(
            clahe,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        gamma_bright = self._apply_gamma(gray_roi, gamma=1.4)
        _decode_attempt(
            gamma_bright,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        gamma_dark = self._apply_gamma(gray_roi, gamma=0.7)
        _decode_attempt(
            gamma_dark,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        _th, th_img = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _decode_attempt(
            th_img,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        adp_img = cv2.adaptiveThreshold(
            clahe,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            8,
        )
        _decode_attempt(
            adp_img,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        unsharp = self._unsharp_mask(clahe)
        _decode_attempt(
            unsharp,
            map_rect=lambda r: r,
            source="zbar_header",
        )
        if headers:
            return headers, dets

        # Fase 2: deskew SOLO de ROI de header (sin tocar imagen completa)
        for angle in (-15, 15, -30, 30, -45, 45):
            for base_img in (gray_roi, clahe, adp_img):
                rot, inv_m = self._rotate_gray_with_inverse(base_img, angle=angle)
                _decode_attempt(
                    rot,
                    map_rect=lambda r, inv=inv_m, ow=gray_roi.shape[1], oh=gray_roi.shape[0]: self._map_rotated_rect_to_original(
                        r,
                        inv_m=inv,
                        out_width=ow,
                        out_height=oh,
                    ),
                    source="zbar_header_deskew",
                )
                if headers:
                    return headers, dets

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

    @staticmethod
    def _scale_rect(
        rect: tuple[int, int, int, int],
        *,
        sx: float,
        sy: float,
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        return (
            int(round(float(x) * sx)),
            int(round(float(y) * sy)),
            max(1, int(round(float(w) * sx))),
            max(1, int(round(float(h) * sy))),
        )

    @staticmethod
    def _apply_gamma(gray: np.ndarray, *, gamma: float) -> np.ndarray:
        gamma_safe = max(0.1, float(gamma))
        inv_gamma = 1.0 / gamma_safe
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
            dtype=np.uint8,
        )
        return cv2.LUT(gray, table)

    @staticmethod
    def _unsharp_mask(gray: np.ndarray) -> np.ndarray:
        blur = cv2.GaussianBlur(gray, (0, 0), 1.0)
        out = cv2.addWeighted(gray, 1.35, blur, -0.35, 0)
        return cv2.normalize(out, None, 0, 255, cv2.NORM_MINMAX)

    @staticmethod
    def _rotate_gray_with_inverse(gray: np.ndarray, *, angle: float) -> tuple[np.ndarray, np.ndarray]:
        h, w = gray.shape[:2]
        center = (w / 2.0, h / 2.0)

        m = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        cos = abs(m[0, 0])
        sin = abs(m[0, 1])

        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        m[0, 2] += (new_w / 2.0) - center[0]
        m[1, 2] += (new_h / 2.0) - center[1]

        rotated = cv2.warpAffine(
            gray,
            m,
            (new_w, new_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        inv_m = cv2.invertAffineTransform(m)
        return rotated, inv_m

    @staticmethod
    def _map_rotated_rect_to_original(
        rect: tuple[int, int, int, int],
        *,
        inv_m: np.ndarray,
        out_width: int,
        out_height: int,
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        pts = np.array(
            [
                [x, y, 1.0],
                [x + w, y, 1.0],
                [x, y + h, 1.0],
                [x + w, y + h, 1.0],
            ],
            dtype=np.float32,
        )
        mapped = pts @ inv_m.T

        xs = np.clip(mapped[:, 0], 0, max(0, out_width - 1))
        ys = np.clip(mapped[:, 1], 0, max(0, out_height - 1))

        min_x = int(np.floor(float(np.min(xs))))
        max_x = int(np.ceil(float(np.max(xs))))
        min_y = int(np.floor(float(np.min(ys))))
        max_y = int(np.ceil(float(np.max(ys))))

        return (
            min_x,
            min_y,
            max(1, max_x - min_x),
            max(1, max_y - min_y),
        )

    @staticmethod
    def _is_valid_header_candidate(value: str) -> bool:
        if not value or not value.isdigit():
            return False
        ln = len(value)
        return ln in (12, 13) or ln >= 18


# ============================================================
# RENDERER
# ============================================================

class TiffScanRenderer:

    def __init__(self, *, jpg_quality: int = 85):

        self.jpg_quality = jpg_quality

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
            pages = TiffZBarMaskedScanner.load_pages_bgr(tiff_path, max_pages=2)

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
        load_started_at = time.perf_counter()

        pages = TiffZBarMaskedScanner.load_pages_bgr(
            tiff_path,
            max_pages=self._scanner.max_pages,
        )
        load_elapsed = max(0.0, time.perf_counter() - load_started_at)

        base = os.path.splitext(os.path.basename(tiff_path))[0]

        return self._scanner.process_pages(
            pages,
            base,
            load_pages_seconds=load_elapsed,
        )

    def scan_with_pages(self, tiff_path: str):
        load_started_at = time.perf_counter()

        pages = TiffZBarMaskedScanner.load_pages_bgr(
            tiff_path,
            max_pages=self._scanner.max_pages,
        )
        load_elapsed = max(0.0, time.perf_counter() - load_started_at)

        base = os.path.splitext(os.path.basename(tiff_path))[0]

        scan = self._scanner.process_pages(
            pages,
            base,
            load_pages_seconds=load_elapsed,
        )

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
