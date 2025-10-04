import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import logging
from typing import List, Tuple, Optional
from models.data_models import RawToken
from models.request_models import RawTokensResponse
from utils.text_utils import text_processor
from utils.currency_utils import currency_detector
from utils.validation_utils import validation_utils
from config.settings import settings

logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR text extraction and raw token processing."""
    
    def __init__(self):
        self.tesseract_config = settings.OCR_CONFIG
        self.min_confidence = settings.MIN_OCR_CONFIDENCE
        
        # Set tesseract command path if configured
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            logger.info(f"Tesseract command set to: {settings.TESSERACT_CMD}")
        else:
            logger.warning("No TESSERACT_CMD configured, using system PATH")
        
        # Test if tesseract is accessible
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            logger.error(f"Failed to access Tesseract: {str(e)}")
    
    async def extract_from_text(self, text: str) -> RawTokensResponse:
        """
        Extract raw tokens from text input.
        
        Args:
            text: Input text to process
            
        Returns:
            RawTokensResponse with extracted tokens
        """
        try:
            # Validate input
            is_valid, error_msg = validation_utils.validate_text_input(text)
            if not is_valid:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="error",
                    reason=error_msg
                )
            
            # Clean and process text
            cleaned_text = text_processor.clean_text(text)
            logger.info(f"Processing text: {cleaned_text[:100]}...")
            
            # Extract numeric tokens
            numeric_tokens = text_processor.extract_numeric_tokens(cleaned_text)
            
            if not numeric_tokens:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="no_amounts_found",
                    reason="No numeric tokens found in text"
                )
            
            # Process tokens and extract amounts
            raw_tokens = []
            for token_text, position, context in numeric_tokens:
                amounts = text_processor.extract_amounts_from_token(token_text)
                if amounts:
                    for amount in amounts:
                        raw_tokens.append(str(amount))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_tokens = []
            for token in raw_tokens:
                if token not in seen:
                    seen.add(token)
                    unique_tokens.append(token)
            
            if not unique_tokens:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="no_amounts_found",
                    reason="No valid amounts found in numeric tokens"
                )
            
            # Detect currency
            currency, currency_confidence = currency_detector.detect_currency(cleaned_text)
            
            # Calculate overall confidence
            # Base confidence on number of tokens found and currency detection
            token_confidence = min(1.0, len(unique_tokens) * 0.2 + 0.4)
            overall_confidence = (token_confidence + currency_confidence) / 2
            
            logger.info(f"Extracted {len(unique_tokens)} tokens with confidence {overall_confidence:.2f}")
            
            return RawTokensResponse(
                raw_tokens=unique_tokens,
                currency_hint=currency.value if currency.value != "UNKNOWN" else None,
                confidence=overall_confidence,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return RawTokensResponse(
                raw_tokens=[],
                confidence=0.0,
                status="error",
                reason=f"Text processing error: {str(e)}"
            )
    
    async def extract_from_image(self, image_data: bytes) -> RawTokensResponse:
        """
        Extract raw tokens from image using OCR.
        
        Args:
            image_data: Image bytes to process
            
        Returns:
            RawTokensResponse with extracted tokens
        """
        try:
            # Validate image data
            is_valid, error_msg = validation_utils.validate_image_data(image_data)
            if not is_valid:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="error",
                    reason=error_msg
                )
            
            logger.info("Processing image for OCR...")
            
            # Load and preprocess image
            image = self._load_and_preprocess_image(image_data)
            if image is None:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="error",
                    reason="Failed to load or process image"
                )
            
            # Perform OCR
            ocr_result = self._perform_ocr(image)
            if not ocr_result:
                return RawTokensResponse(
                    raw_tokens=[],
                    confidence=0.0,
                    status="no_amounts_found",
                    reason="No text detected in image"
                )
            
            extracted_text, ocr_confidence = ocr_result
            logger.info(f"OCR extracted text: {extracted_text[:100]}...")
            
            # Apply OCR corrections
            corrected_text, corrections = text_processor.correct_ocr_digits(extracted_text)
            if corrections:
                logger.info(f"Applied OCR corrections: {corrections}")
            
            # Process as text
            text_result = await self.extract_from_text(corrected_text)
            
            # Adjust confidence based on OCR quality
            if text_result.status == "success":
                # Combine OCR confidence with text processing confidence
                combined_confidence = (ocr_confidence + text_result.confidence) / 2
                text_result.confidence = combined_confidence
                # Preserve the original OCR text for better source context
                text_result.original_text = corrected_text
            
            return text_result
            
        except Exception as e:
            logger.error(f"Error in image OCR: {str(e)}")
            return RawTokensResponse(
                raw_tokens=[],
                confidence=0.0,
                status="error",
                reason=f"Image processing error: {str(e)}"
            )
    
    def _load_and_preprocess_image(self, image_data: bytes) -> Optional[np.ndarray]:
        """
        Load and preprocess image for better OCR results.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Preprocessed image as numpy array, or None if failed
        """
        try:
            # Load image
            image_pil = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Convert to OpenCV format
            image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            
            # Preprocess for better OCR
            image_cv = self._enhance_for_ocr(image_cv)
            
            return image_cv
            
        except Exception as e:
            logger.error(f"Error loading image: {str(e)}")
            return None
    
    def _enhance_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Enhanced image preprocessing for better OCR results.
        Based on the working enhanced OCR test.
        
        Args:
            image: Input image
            
        Returns:
            Best enhanced image for OCR
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try multiple enhancement techniques and pick the best one
        enhanced_images = {}
        
        # 1. Original grayscale
        enhanced_images['original'] = gray
        
        # 2. Gaussian blur + OTSU threshold
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        enhanced_images['otsu'] = thresh1
        
        # 3. Adaptive threshold
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        enhanced_images['adaptive'] = adaptive
        
        # 4. Contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(gray)
        enhanced_images['contrast'] = contrast_enhanced
        
        # 5. Morphological operations
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
        enhanced_images['morph'] = morph
        
        # Test each enhancement and return the original (which worked best in our test)
        # For now, return the original grayscale as it worked best in our enhanced test
        return gray
    
    def _perform_ocr(self, image: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        Perform OCR on preprocessed image using multiple configurations.
        Based on the working enhanced OCR test.
        
        Args:
            image: Preprocessed image
            
        Returns:
            Tuple of (extracted_text, confidence) or None if failed
        """
        try:
            # Multiple OCR configurations to try (from our working test)
            configs = {
                'digits_only': '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,Rs',
                'default': '--oem 3 --psm 6',
                'single_column': '--oem 3 --psm 4',
                'single_text_line': '--oem 3 --psm 7',
                'preserve_interword_spaces': '--oem 3 --psm 6 -c preserve_interword_spaces=1'
            }
            
            best_result = None
            best_confidence = 0.0
            best_text = ""
            
            for config_name, config in configs.items():
                try:
                    # Extract text with this configuration
                    text = pytesseract.image_to_string(image, config=config, lang='eng')
                    
                    if not text or not text.strip():
                        continue
                        
                    # Get confidence data for this configuration
                    try:
                        ocr_data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                        if confidences:
                            avg_confidence = sum(confidences) / len(confidences) / 100.0
                        else:
                            avg_confidence = 0.3  # Default confidence
                    except:
                        avg_confidence = 0.3  # Fallback confidence
                    
                    # Score this result based on text length and confidence
                    text_length_score = min(1.0, len(text.strip()) / 50.0)  # Normalize by expected length
                    combined_score = (avg_confidence + text_length_score) / 2
                    
                    logger.info(f"OCR config '{config_name}': {len(text.strip())} chars, confidence {avg_confidence:.2f}, score {combined_score:.2f}")
                    
                    # Keep the best result
                    if combined_score > best_confidence:
                        best_confidence = combined_score
                        best_text = text.strip()
                        best_result = (best_text, best_confidence)
                        
                except Exception as config_error:
                    logger.warning(f"OCR config '{config_name}' failed: {str(config_error)}")
                    continue
            
            if best_result and best_confidence >= self.min_confidence:
                logger.info(f"Best OCR result: {len(best_text)} characters with confidence {best_confidence:.2f}")
                return best_result
            elif best_result:
                # Even if confidence is low, return the best result we got
                logger.warning(f"Low confidence OCR result: {best_confidence:.2f}, but returning anyway")
                return best_result
            else:
                logger.warning("No valid OCR results from any configuration")
                return None
            
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            return None

# Global OCR service instance
ocr_service = OCRService()