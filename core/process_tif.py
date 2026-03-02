from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, TypedDict, Literal

import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol


BBox = Tuple[int, int, int, int]
TroquelEstado = Literal["V", "A", "R"]


class HeaderDet(TypedDict):
    page_idx: int
    type: str             # "CODE128" | "CODE39"
    value: str
    bbox: BBox            # coords globales sobre la página
    source: str           # "full+zbar"


class TroquelDet(TypedDict):
    page_idx: int
    type: str             # "EAN13"
    value: str
    bbox: BBox            # coords globales sobre la página
    source: str           # "tile+zbar"
    masked: bool          # siempre True acá


class FilesOut(TypedDict):
    front_bytes: Optional[bytes]
    back_bytes: Optional[bytes]



@dataclass(frozen=True)
class ScanOut:
    base_name: str
    headers: List[str]                    # values (headers)
    troqueles: List[str]                  # values (ean13) (permite duplicados reales)
    header_detections: List[HeaderDet]    # para render
    troquel_detections: List[TroquelDet]  # para render


# ============================================================
# Scanner: FULL solo headers + MASKED solo troqueles
# ============================================================
class TiffZBarMaskedScanner:
    """
    FULL scan: solo headers (CODE128 / CODE39)
    TILED+MASK: solo troqueles (EAN13), con enmascarado en memoria para evitar re-detecciones
    """

    def __init__(
        self,
        *,
        tile: int = 700,
        overlap: float = 0.40,
        dup_dist_px: int = 240,
        allow_duplicates: bool = True,
        max_passes: int = 6,
        mask_pad: int = 18,
        max_pages: int = 2,
        header_types: Tuple[str, ...] = ("CODE128", "CODE39"),
    ) -> None:
        self.tile = int(tile)
        self.overlap = float(overlap)
        self.dup_dist_px = int(dup_dist_px)
        self.allow_duplicates = bool(allow_duplicates)
        self.max_passes = int(max_passes)
        self.mask_pad = int(mask_pad)
        self.max_pages = int(max_pages)
        self.header_types = tuple(header_types)

    def process(self, tiff_path: str) -> ScanOut:
        tiff_path = os.path.abspath(tiff_path)
        if not os.path.isfile(tiff_path):
            raise FileNotFoundError(tiff_path)

        pages = self.load_pages_bgr(tiff_path)
        base = os.path.splitext(os.path.basename(tiff_path))[0]

        all_headers: List[str] = []
        all_troqueles: List[str] = []
        header_dets: List[HeaderDet] = []
        troquel_dets: List[TroquelDet] = []

        for page_idx, page_bgr in enumerate(pages[: self.max_pages]):
            # 1) headers (full)
            h_vals, h_dets = self._scan_page_full_only_headers(
                page_bgr,
                page_idx=page_idx,
                header_types=self.header_types,
            )
            all_headers.extend(h_vals)
            header_dets.extend(h_dets)

            # 2) troqueles (masked)
            t_vals, t_dets = self._scan_page_masked_only_troqueles(
                page_bgr,
                page_idx=page_idx,
                tile=self.tile,
                overlap=self.overlap,
                dup_dist_px=self.dup_dist_px,
                allow_duplicates=self.allow_duplicates,
                max_passes=self.max_passes,
                mask_pad=self.mask_pad,
            )
            all_troqueles.extend(t_vals)
            troquel_dets.extend(t_dets)

        return ScanOut(
            base_name=base,
            headers=all_headers,
            troqueles=all_troqueles,
            header_detections=header_dets,
            troquel_detections=troquel_dets,
        )

    def process_pages(self, pages: List[np.ndarray], base_name: str) -> ScanOut:
        all_headers: List[str] = []
        all_troqueles: List[str] = []
        header_dets: List[HeaderDet] = []
        troquel_dets: List[TroquelDet] = []

        for page_idx, page_bgr in enumerate(pages[: self.max_pages]):
            h_vals, h_dets = self._scan_page_full_only_headers(
                page_bgr,
                page_idx=page_idx,
                header_types=self.header_types,
            )
            all_headers.extend(h_vals)
            header_dets.extend(h_dets)

            t_vals, t_dets = self._scan_page_masked_only_troqueles(
                page_bgr,
                page_idx=page_idx,
                tile=self.tile,
                overlap=self.overlap,
                dup_dist_px=self.dup_dist_px,
                allow_duplicates=self.allow_duplicates,
                max_passes=self.max_passes,
                mask_pad=self.mask_pad,
            )
            all_troqueles.extend(t_vals)
            troquel_dets.extend(t_dets)

        return ScanOut(
            base_name=base_name,
            headers=all_headers,
            troqueles=all_troqueles,
            header_detections=header_dets,
            troquel_detections=troquel_dets,
        )

    # ---------- IO ----------
    @staticmethod
    def load_pages_bgr(tiff_path: str) -> List[np.ndarray]:
        # Intento cv2.imreadmulti
        try:
            ok, pages = cv2.imreadmulti(tiff_path, flags=cv2.IMREAD_COLOR)
            if ok and pages:
                return pages
        except Exception:
            pass

        # Fallback PIL
        pages: List[np.ndarray] = []
        img = Image.open(tiff_path)
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
        return pages

    # ---------- Utils ----------
    @staticmethod
    def _clamp(v: int, lo: int, hi: int) -> int:
        return lo if v < lo else hi if v > hi else v

    @staticmethod
    def _bbox_center(b: BBox) -> Tuple[float, float]:
        x, y, w, h = b
        return (x + w / 2.0, y + h / 2.0)

    @staticmethod
    def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return float((dx * dx + dy * dy) ** 0.5)

    # ---------- Decode ----------
    @staticmethod
    def _decode_headers(gray: np.ndarray) -> List[Tuple[str, str, BBox]]:
        barcodes = zbar_decode(
            gray,
            symbols=[
                ZBarSymbol.CODE128,
                ZBarSymbol.CODE39,
            ],
        )
        out: List[Tuple[str, str, BBox]] = []
        for b in barcodes:
            value = (b.data.decode("utf-8") or "").strip()
            btype = (b.type or "").strip()
            x, y, w, h = b.rect
            if value and w > 0 and h > 0:
                out.append((btype, value, (int(x), int(y), int(w), int(h))))
        return out

    @staticmethod
    def _decode_troqueles(gray: np.ndarray) -> List[Tuple[str, str, BBox]]:
        barcodes = zbar_decode(
            gray,
            symbols=[
                ZBarSymbol.EAN13,
                # ZBarSymbol.EAN8,  # solo si realmente lo usás
            ],
        )
        out: List[Tuple[str, str, BBox]] = []
        for b in barcodes:
            value = (b.data.decode("utf-8") or "").strip()
            btype = (b.type or "").strip()
            x, y, w, h = b.rect
            if value and w > 0 and h > 0:
                out.append((btype, value, (int(x), int(y), int(w), int(h))))
        return out

    # ---------- Tiling ----------
    @staticmethod
    def _iter_tiles(W: int, H: int, tile: int, overlap: float) -> List[BBox]:
        tile = max(64, int(tile))
        overlap = float(overlap)
        overlap = 0.0 if overlap < 0 else 0.9 if overlap > 0.9 else overlap

        step = int(round(tile * (1.0 - overlap)))
        step = max(32, step)

        tiles: List[BBox] = []

        ys = list(range(0, max(1, H - tile + 1), step))
        xs = list(range(0, max(1, W - tile + 1), step))

        if not ys or ys[-1] != H - tile:
            ys.append(max(0, H - tile))
        if not xs or xs[-1] != W - tile:
            xs.append(max(0, W - tile))

        for y in ys:
            for x in xs:
                w = min(tile, W - x)
                h = min(tile, H - y)
                tiles.append((x, y, w, h))

        return tiles

    # ---------- Mask ----------
    @classmethod
    def _mask_region(cls, gray: np.ndarray, bbox: BBox, pad: int = 18) -> None:
        H, W = gray.shape[:2]
        x, y, w, h = bbox

        x0 = cls._clamp(x - pad, 0, W - 1)
        y0 = cls._clamp(y - pad, 0, H - 1)
        x1 = cls._clamp(x + w + pad, 0, W)
        y1 = cls._clamp(y + h + pad, 0, H)

        if x1 > x0 and y1 > y0:
            gray[y0:y1, x0:x1] = 255

    # ---------- Core page scan ----------
    @classmethod
    def _scan_page_masked_only_troqueles(
        cls,
        page_bgr: np.ndarray,
        *,
        page_idx: int,
        tile: int,
        overlap: float,
        dup_dist_px: int,
        allow_duplicates: bool,
        max_passes: int,
        mask_pad: int,
    ) -> Tuple[List[str], List[TroquelDet]]:
        troqueles: List[str] = []
        troquel_dets: List[TroquelDet] = []

        occ_by_value: Dict[str, List[Tuple[float, float]]] = {}

        gray0 = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
        gray = gray0.copy()

        H, W = gray.shape[:2]
        tiles = cls._iter_tiles(W, H, tile=tile, overlap=overlap)

        for _pass in range(max_passes):
            any_new = False

            for (tx, ty, tw, th) in tiles:
                roi = gray[ty : ty + th, tx : tx + tw]
                if roi.size == 0:
                    continue

                hits = cls._decode_troqueles(roi)
                if not hits:
                    continue

                for btype, value, (rx, ry, rw, rh) in hits:
                    if not (btype == "EAN13" and value.isdigit() and len(value) == 13):
                        continue

                    det_bbox: BBox = (tx + rx, ty + ry, int(rw), int(rh))
                    c = cls._bbox_center(det_bbox)
                    prev = occ_by_value.get(value, [])

                    if allow_duplicates:
                        # duplicados reales: colapsar solo misma ocurrencia
                        if any(cls._dist(c, pc) <= dup_dist_px for pc in prev):
                            continue
                    else:
                        # no duplicados por value
                        if value in occ_by_value:
                            continue

                    occ_by_value.setdefault(value, []).append(c)

                    troqueles.append(value)
                    troquel_dets.append(
                        {
                            "page_idx": page_idx,
                            "source": "tile+zbar",
                            "type": "EAN13",
                            "value": value,
                            "bbox": det_bbox,
                            "masked": True,
                        }
                    )

                    cls._mask_region(gray, det_bbox, pad=mask_pad)
                    any_new = True

            if not any_new:
                break

        return troqueles, troquel_dets

    @classmethod
    def _scan_page_full_only_headers(
        cls,
        page_bgr: np.ndarray,
        *,
        page_idx: int,
        header_types: Tuple[str, ...] = ("CODE128", "CODE39"),
    ) -> Tuple[List[str], List[HeaderDet]]:
        headers: List[str] = []
        header_dets: List[HeaderDet] = []

        gray0 = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
        full_hits = cls._decode_headers(gray0)

        for btype, value, bb in full_hits:
            if btype in header_types:
                headers.append(value)
                header_dets.append(
                    {
                        "page_idx": page_idx,
                        "source": "full+zbar",
                        "type": btype,
                        "value": value,
                        "bbox": bb,
                    }
                )

        return headers, header_dets


# ============================================================
# Renderer: dibuja desde ScanOut (sin re-scan)
# ============================================================
class TiffScanRenderer:
    def __init__(
        self,
        *,
        max_pages: int = 2,
        rect_thickness: int = 2,
        font_scale: float = 0.6,
        font_thickness: int = 2,
        color_header_bgr: Tuple[int, int, int] = (255, 0, 0),
        color_v_bgr: Tuple[int, int, int] = (0, 181, 26),
        color_a_bgr: Tuple[int, int, int] = (0, 255, 255),
        color_r_bgr: Tuple[int, int, int] = (0, 0, 255),
        jpg_quality: int = 85,
    ) -> None:
        self.max_pages = int(max_pages)
        self.rect_thickness = int(rect_thickness)
        self.font_scale = float(font_scale)
        self.font_thickness = int(font_thickness)

        self.C_HEADER = color_header_bgr
        self.C_V = color_v_bgr
        self.C_A = color_a_bgr
        self.C_R = color_r_bgr

        self.jpg_quality = int(jpg_quality)

    def render_bytes(
        self,
        tiff_path: str,
        scan: ScanOut,
        *,
        estado_por_codebar: Optional[Dict[str, TroquelEstado]] = None,
        estado_resolver: Optional[Callable[[str], TroquelEstado]] = None,
        draw_headers: bool = True,
        draw_troqueles: bool = True,
        pages_loader: Optional[Callable[[str], List[np.ndarray]]] = None,
        pages: Optional[List[np.ndarray]] = None,
    ) -> FilesOut:
        if pages is None:
            loader = pages_loader or TiffZBarMaskedScanner.load_pages_bgr
            pages = loader(tiff_path)

        out: FilesOut = {"front_bytes": None, "back_bytes": None}

        def get_estado(codebar: str) -> TroquelEstado:
            if estado_por_codebar and codebar in estado_por_codebar:
                return estado_por_codebar[codebar]
            if estado_resolver:
                return estado_resolver(codebar)
            return "A"

        for page_idx, img in enumerate(pages[: self.max_pages]):
            canvas = img.copy()

            if draw_headers:
                for d in scan.header_detections:
                    if d["page_idx"] != page_idx:
                        continue
                    x, y, w, h = d["bbox"]
                    val = d["value"]
                    typ = d["type"]
                    cv2.rectangle(canvas, (x, y), (x + w, y + h), self.C_HEADER, self.rect_thickness)
                    yy = y - 10 if y > 20 else y + h + 20
                    cv2.putText(
                        canvas,
                        f"{typ}:{val}",
                        (x, max(0, yy)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.font_scale,
                        self.C_HEADER,
                        self.font_thickness,
                    )

            if draw_troqueles:
                for d in scan.troquel_detections:
                    if d["page_idx"] != page_idx:
                        continue
                    x, y, w, h = d["bbox"]
                    val = d["value"]
                    estado = get_estado(val)
                    color = self.C_V if estado == "V" else (self.C_R if estado == "R" else self.C_A)

                    cv2.rectangle(canvas, (x, y), (x + w, y + h), color, self.rect_thickness)
                    yy = y - 10 if y > 20 else y + h + 20
                    cv2.putText(
                        canvas,
                        f"EAN13:{val} [{estado}]",
                        (x, max(0, yy)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.font_scale,
                        color,
                        self.font_thickness,
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
# FACHADA (lo que usa el service)
# ============================================================
class TiffProcessor:
    """
    Compatible con tu uso actual en TiffService:
      - scan(tiff_path) -> ScanOut (headers/troqueles + detections)
      - render(tiff_path, scan, output_dir, estado_por_codebar|resolver) -> FilesOut
    """

    def __init__(
        self,
        *,
        tile: int = 700,
        overlap: float = 0.40,
        dup_dist_px: int = 220,
        allow_duplicates: bool = True,
        max_passes: int = 6,
        mask_pad: int = 18,
        max_pages: int = 2,
        header_types: Tuple[str, ...] = ("CODE128", "CODE39"),
    ) -> None:
        self._scanner = TiffZBarMaskedScanner(
            tile=tile,
            overlap=overlap,
            dup_dist_px=dup_dist_px,
            allow_duplicates=allow_duplicates,
            max_passes=max_passes,
            mask_pad=mask_pad,
            max_pages=max_pages,
            header_types=header_types,
        )
        self._renderer = TiffScanRenderer(max_pages=max_pages)

    def scan(self, tiff_path: str) -> ScanOut:
        return self._scanner.process(tiff_path)

    def render_bytes(
        self,
        *,
        tiff_path: str,
        scan: ScanOut,
        estado_por_codebar: Optional[Dict[str, TroquelEstado]] = None,
        estado_resolver: Optional[Callable[[str], TroquelEstado]] = None,
        draw_headers: bool = True,
        draw_troqueles: bool = True,
        pages: Optional[List[np.ndarray]] = None,
    ) -> FilesOut:
        return self._renderer.render_bytes(
            tiff_path=tiff_path,
            scan=scan,
            estado_por_codebar=estado_por_codebar,
            estado_resolver=estado_resolver,
            draw_headers=draw_headers,
            draw_troqueles=draw_troqueles,
            pages_loader=TiffZBarMaskedScanner.load_pages_bgr,
            pages=pages,
        )

    def scan_with_pages(self, tiff_path: str) -> tuple[ScanOut, List[np.ndarray]]:
        pages = TiffZBarMaskedScanner.load_pages_bgr(tiff_path)
        base = os.path.splitext(os.path.basename(tiff_path))[0]
        scan = self._scanner.process_pages(pages, base_name=base)
        return scan, pages


