"""Tests for multimodal support"""
import pytest
from orion.multimodal import MIMEDetector, MediaType, MultimodalProcessor


class TestMIMEDetector:
    def test_detect_text(self):
        from pathlib import Path
        mime = MIMEDetector.detect_from_path(Path("test.txt"))
        assert mime == "text/plain"

    def test_detect_image(self):
        from pathlib import Path
        mime = MIMEDetector.detect_from_path(Path("test.png"))
        assert mime == "image/png"

    def test_detect_unknown(self):
        from pathlib import Path
        mime = MIMEDetector.detect_from_path(Path("test.xyz"))
        assert mime == "application/octet-stream"

    def test_detect_png_content(self):
        mime = MIMEDetector.detect_from_content(b'\x89PNG\r\n\x1a\n')
        assert mime == "image/png"

    def test_detect_pdf_content(self):
        mime = MIMEDetector.detect_from_content(b'%PDF-1.4')
        assert mime == "application/pdf"


class TestMultimodalProcessor:
    def test_classify_text(self):
        from pathlib import Path
        processor = MultimodalProcessor()
        result = processor.classify(Path("test.txt"))
        assert result == MediaType.TEXT
