"""
ORION Multimodal Support
=========================
Processing of images, audio, and other media types.

Features:
- Image metadata extraction
- Audio metadata extraction
- Text extraction from structured data
- MIME type detection
- Content fingerprinting
"""

import os
import re
import json
import base64
import hashlib
import struct
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging

logger = logging.getLogger("orion.multimodal")


class MediaType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass
class MediaMetadata:
    """Metadata extracted from media file"""
    media_type: MediaType = MediaType.UNKNOWN
    mime_type: str = ""
    size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    format: str = ""
    encoding: str = ""
    hash_sha256: str = ""
    text_content: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_type": self.media_type.value,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "duration_seconds": self.duration_seconds,
            "format": self.format,
            "encoding": self.encoding,
            "hash_sha256": self.hash_sha256,
            "text_content": self.text_content[:200] if self.text_content else "",
            "properties": self.properties
        }


class MIMEDetector:
    """Detect MIME types from content and extensions"""
    
    EXTENSION_MAP = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
        '.yaml': 'application/x-yaml',
        '.yml': 'application/x-yaml',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
    }
    
    MAGIC_BYTES: Dict[bytes, str] = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xff\xd8\xff': 'image/jpeg',
        b'GIF89a': 'image/gif',
        b'GIF87a': 'image/gif',
        b'RIFF': 'image/webp',  # WEBP starts with RIFF
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/zip',
        b'ID3': 'audio/mpeg',
    }
    
    @classmethod
    def detect_from_path(cls, path: Path) -> str:
        """Detect MIME type from file path"""
        ext = path.suffix.lower()
        return cls.EXTENSION_MAP.get(ext, 'application/octet-stream')
    
    @classmethod
    def detect_from_content(cls, content: bytes) -> str:
        """Detect MIME type from content bytes"""
        for magic, mime in cls.MAGIC_BYTES.items():
            if content.startswith(magic):
                return mime
        return 'application/octet-stream'


class ImageProcessor:
    """Process image content"""
    
    @staticmethod
    def get_metadata(path: Path) -> Optional[MediaMetadata]:
        """Extract image metadata"""
        try:
            content = path.read_bytes()
            mime = MIMEDetector.detect_from_content(content)
            
            meta = MediaMetadata(
                media_type=MediaType.IMAGE,
                mime_type=mime or MIMEDetector.detect_from_path(path),
                size_bytes=len(content),
                format=path.suffix.lower().lstrip('.'),
                hash_sha256=hashlib.sha256(content).hexdigest()
            )
            
            if mime == 'image/png':
                meta.width = struct.unpack('>I', content[16:20])[0]
                meta.height = struct.unpack('>I', content[20:24])[0]
            elif mime == 'image/jpeg':
                # Extract dimensions from JPEG
                i = 2
                while i < len(content) - 1:
                    if content[i] == 0xFF and content[i+1] == 0xC0:
                        meta.height = struct.unpack('>H', content[i+5:i+7])[0]
                        meta.width = struct.unpack('>H', content[i+7:i+9])[0]
                        break
                    i += 2
            
            return meta
        except Exception as e:
            logger.warning(f"Error processing image {path}: {e}")
            return None
    
    @staticmethod
    def encode_base64(path: Path) -> Optional[str]:
        """Encode image to base64"""
        try:
            content = path.read_bytes()
            return base64.b64encode(content).decode('utf-8')
        except Exception as e:
            logger.warning(f"Error encoding image {path}: {e}")
            return None


class AudioProcessor:
    """Process audio content"""
    
    @staticmethod
    def get_metadata(path: Path) -> Optional[MediaMetadata]:
        """Extract audio metadata"""
        try:
            content = path.read_bytes()
            mime = MIMEDetector.detect_from_content(content)
            
            meta = MediaMetadata(
                media_type=MediaType.AUDIO,
                mime_type=mime or MIMEDetector.detect_from_path(path),
                size_bytes=len(content),
                format=path.suffix.lower().lstrip('.'),
                hash_sha256=hashlib.sha256(content).hexdigest()
            )
            
            # Try to estimate duration from MP3 frames
            if mime == 'audio/mpeg' or path.suffix.lower() == '.mp3':
                # Rough estimate: ~1MB per minute for 128kbps MP3
                if len(content) > 0:
                    estimated_seconds = (len(content) / (128 * 1024 / 8)) * 60
                    meta.duration_seconds = round(estimated_seconds, 1)
            
            return meta
        except Exception as e:
            logger.warning(f"Error processing audio {path}: {e}")
            return None


class DocumentProcessor:
    """Process text documents"""
    
    @staticmethod
    def extract_text(path: Path) -> Optional[str]:
        """Extract text from document"""
        try:
            content = path.read_bytes()
            mime = MIMEDetector.detect_from_content(content) or MIMEDetector.detect_from_path(path)
            
            if mime == 'text/plain' or mime == 'text/markdown':
                return content.decode('utf-8', errors='replace')
            elif mime == 'application/json':
                data = json.loads(content)
                return json.dumps(data, indent=2, ensure_ascii=False)
            else:
                return content.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Error extracting text from {path}: {e}")
            return None


class MultimodalProcessor:
    """
    Unified processor for multiple media types.
    """
    
    def __init__(self):
        self.processors = {
            MediaType.IMAGE: ImageProcessor(),
            MediaType.AUDIO: AudioProcessor(),
            MediaType.DOCUMENT: DocumentProcessor(),
        }
        logger.info("Multimodal Processor initialized")
    
    def process(self, path: Path) -> Optional[MediaMetadata]:
        """Process any media file and extract metadata"""
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return None
        
        mime = MIMEDetector.detect_from_path(path)
        content = path.read_bytes()
        
        base_meta = MediaMetadata(
            mime_type=mime,
            size_bytes=len(content),
            format=path.suffix.lower().lstrip('.'),
            hash_sha256=hashlib.sha256(content).hexdigest()
        )
        
        if mime.startswith('image/'):
            base_meta.media_type = MediaType.IMAGE
            img_meta = ImageProcessor.get_metadata(path)
            if img_meta:
                base_meta.width = img_meta.width
                base_meta.height = img_meta.height
        
        elif mime.startswith('audio/'):
            base_meta.media_type = MediaType.AUDIO
            audio_meta = AudioProcessor.get_metadata(path)
            if audio_meta:
                base_meta.duration_seconds = audio_meta.duration_seconds
        
        elif mime.startswith('text/') or mime == 'application/json':
            base_meta.media_type = MediaType.TEXT
            text = DocumentProcessor.extract_text(path)
            if text:
                base_meta.text_content = text[:1000]
        
        elif mime == 'application/pdf':
            base_meta.media_type = MediaType.DOCUMENT
        
        else:
            base_meta.media_type = MediaType.UNKNOWN
        
        return base_meta
    
    def classify(self, path: Path) -> MediaType:
        """Classify media type of a file"""
        mime = MIMEDetector.detect_from_path(path)
        
        if mime.startswith('image/'):
            return MediaType.IMAGE
        elif mime.startswith('audio/'):
            return MediaType.AUDIO
        elif mime.startswith('video/'):
            return MediaType.VIDEO
        elif mime.startswith('text/'):
            return MediaType.TEXT
        elif mime in ['application/json', 'application/xml', 'application/x-yaml']:
            return MediaType.DATA
        elif mime == 'application/pdf':
            return MediaType.DOCUMENT
        
        return MediaType.UNKNOWN


# Global instance
_multimodal: Optional[MultimodalProcessor] = None

def get_multimodal() -> MultimodalProcessor:
    global _multimodal
    if _multimodal is None:
        _multimodal = MultimodalProcessor()
    return _multimodal
