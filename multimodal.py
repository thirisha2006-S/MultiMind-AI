"""
Multi-Modal Support for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Image text extraction (OCR)
- Audio transcription
- PDF processing (integration with parsers)
- Unified multimodal input handling
- File type detection and routing
"""

import os
import io
import base64
import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class MultimodalInput:
    """Represents a multimodal input."""
    input_type: str  # "text", "image", "audio", "pdf", "docx", "excel"
    filename: Optional[str] = None
    text_content: Optional[str] = None
    image_data: Optional[bytes] = None
    audio_data: Optional[bytes] = None
    metadata: Dict = field(default_factory=dict)
    extracted_text: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        # Don't serialize raw bytes
        data.pop("image_data", None)
        data.pop("audio_data", None)
        return data


class OCRProcessor:
    """Extract text from images using OCR."""

    def __init__(self):
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import pytesseract
            from PIL import Image
            return True
        except ImportError:
            logger.warning("[Multimodal] pytesseract/PIL not available for OCR. Install: pip install pytesseract Pillow")
            return False

    def extract_text(self, image_data: bytes, filename: str = "image.png") -> str:
        """Extract text from image bytes."""
        if not self.available:
            raise ImportError("pytesseract and Pillow are required for OCR. Install: pip install pytesseract Pillow")
        
        import pytesseract
        from PIL import Image
        
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        text = pytesseract.image_to_string(image)
        return text.strip()

    def extract_text_from_base64(self, base64_str: str, filename: str = "image.png") -> str:
        """Extract text from base64-encoded image."""
        image_data = base64.b64decode(base64_str)
        return self.extract_text(image_data, filename)


class AudioProcessor:
    """Transcribe audio files to text."""

    def __init__(self):
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import whisper
            return True
        except ImportError:
            logger.warning("[Multimodal] whisper not available for audio transcription. Install: pip install openai-whisper")
            return False

    def transcribe(self, audio_data: bytes, filename: str = "audio.mp3", model: str = "base") -> str:
        """Transcribe audio to text."""
        if not self.available:
            raise ImportError("openai-whisper is required for audio transcription. Install: pip install openai-whisper")
        
        import whisper
        
        # Save to temp file (whisper requires file path)
        temp_path = f"temp_{filename}"
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        try:
            model = whisper.load_model(model)
            result = model.transcribe(temp_path)
            text = result.get("text", "").strip()
            return text
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def transcribe_base64(self, base64_str: str, filename: str = "audio.mp3", model: str = "base") -> str:
        """Transcribe base64-encoded audio."""
        audio_data = base64.b64decode(base64_str)
        return self.transcribe(audio_data, filename, model)


class MultiModalProcessor:
    """Unified processor for multimodal inputs."""

    SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    SUPPORTED_AUDIO_TYPES = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".aac"}
    SUPPORTED_DOC_TYPES = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".md"}

    def __init__(self):
        self.ocr = OCRProcessor()
        self.audio = AudioProcessor()
        self.parsers_available = self._check_parsers()

    def _check_parsers(self) -> bool:
        try:
            from parsers import get_document_parser
            return True
        except ImportError:
            return False

    def detect_type(self, filename: str) -> str:
        """Detect input type from filename."""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in self.SUPPORTED_IMAGE_TYPES:
            return "image"
        elif ext in self.SUPPORTED_AUDIO_TYPES:
            return "audio"
        elif ext in self.SUPPORTED_DOC_TYPES:
            return "document"
        else:
            return "unknown"

    def process(self, file_data: bytes, filename: str, user_id: Optional[str] = None) -> MultimodalInput:
        """
        Process a multimodal input file.
        
        Returns:
            MultimodalInput with extracted text and metadata
        """
        input_type = self.detect_type(filename)
        metadata = {
            "filename": filename,
            "file_size_bytes": len(file_data),
            "detected_type": input_type,
        }
        
        extracted_text = None
        
        if input_type == "image":
            try:
                extracted_text = self.ocr.extract_text(file_data, filename)
                metadata["ocr_available"] = True
                metadata["ocr_text_length"] = len(extracted_text) if extracted_text else 0
            except Exception as e:
                logger.error(f"[Multimodal] OCR failed for {filename}: {e}")
                metadata["ocr_available"] = False
                metadata["ocr_error"] = str(e)
        
        elif input_type == "audio":
            try:
                extracted_text = self.audio.transcribe(file_data, filename)
                metadata["transcription_available"] = True
                metadata["transcription_length"] = len(extracted_text) if extracted_text else 0
            except Exception as e:
                logger.error(f"[Multimodal] Transcription failed for {filename}: {e}")
                metadata["transcription_available"] = False
                metadata["transcription_error"] = str(e)
        
        elif input_type == "document":
            try:
                from parsers import parse_document
                doc = parse_document(file_data, filename, user_id=user_id)
                extracted_text = doc.text
                metadata["page_count"] = doc.pages
                metadata["document_metadata"] = doc.metadata
                metadata["chunk_count"] = len(doc.chunks)
            except Exception as e:
                logger.error(f"[Multimodal] Document parsing failed for {filename}: {e}")
                metadata["parsing_error"] = str(e)
        
        return MultimodalInput(
            input_type=input_type,
            filename=filename,
            text_content=extracted_text,
            image_data=file_data if input_type == "image" else None,
            audio_data=file_data if input_type == "audio" else None,
            metadata=metadata,
            extracted_text=extracted_text,
        )

    def process_text_and_file(
        self,
        text: str,
        file_data: Optional[bytes] = None,
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[str, MultimodalInput]:
        """
        Process combined text + file input.
        
        Returns:
            (combined_text_for_query, multimodal_input)
        """
        multimodal_input = None
        
        if file_data and filename:
            multimodal_input = self.process(file_data, filename, user_id)
            if multimodal_input.extracted_text:
                text = f"{text}\n\n[Attached file: {filename}]\n{multimodal_input.extracted_text}"
        
        return text, multimodal_input

    def get_supported_types(self) -> Dict[str, list]:
        """Get supported file types by category."""
        return {
            "images": list(self.SUPPORTED_IMAGE_TYPES),
            "audio": list(self.SUPPORTED_AUDIO_TYPES),
            "documents": list(self.SUPPORTED_DOC_TYPES),
        }


# Global multimodal processor instance
_multimodal_processor: Optional[MultiModalProcessor] = None


def get_multimodal_processor() -> MultiModalProcessor:
    """Get or create the global multimodal processor."""
    global _multimodal_processor
    if _multimodal_processor is None:
        _multimodal_processor = MultiModalProcessor()
    return _multimodal_processor


def process_file(file_data: bytes, filename: str, user_id: Optional[str] = None) -> MultimodalInput:
    """Convenience function to process a file."""
    processor = get_multimodal_processor()
    return processor.process(file_data, filename, user_id)


def process_input(text: str, file_data: Optional[bytes] = None, filename: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[str, Optional[MultimodalInput]]:
    """Convenience function to process combined text + file input."""
    processor = get_multimodal_processor()
    return processor.process_text_and_file(text, file_data, filename, user_id)
