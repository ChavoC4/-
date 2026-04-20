from __future__ import annotations

import re

try:
    import ddddocr
except ModuleNotFoundError:  # pragma: no cover - handled at runtime.
    ddddocr = None

_DIGIT_PATTERN = re.compile(r"\d")


class CaptchaSolver:
    def __init__(self) -> None:
        if ddddocr is None:
            self._ocr = None
        else:
            self._ocr = ddddocr.DdddOcr(show_ad=False)

    def solve(self, image_bytes: bytes) -> str:
        if self._ocr is None:
            raise RuntimeError(
                "ddddocr is not installed. Install dependencies from requirements.txt "
                "before running the scraper."
            )
        raw = self._ocr.classification(image_bytes)
        digits = "".join(_DIGIT_PATTERN.findall(raw))
        if len(digits) < 4:
            raise RuntimeError(f"Captcha OCR failed, got {raw!r}")
        return digits[:4]
