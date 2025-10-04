import logging
from typing import Optional
from models.request_models import ProcessingResponse, AmountItem
from services.ocr_service import ocr_service
from services.normalization_service import normalization_service
from services.classification_service import classification_service
from utils.currency_utils import currency_detector
from utils.validation_utils import validation_utils
from config.settings import settings

logger = logging.getLogger(__name__)

class AmountDetectionPipeline:
    """Main pipeline orchestrating the 4-step amount detection process."""
    
    def __init__(self):
        self.processing_threshold = settings.PROCESSING_CONFIDENCE_THRESHOLD
    
    async def process_text(self, text: str) -> ProcessingResponse:
        """
        Process text input through the complete pipeline.
        
        Args:
            text: Input text to process
            
        Returns:
            ProcessingResponse with final results
        """
        try:
            logger.info("Starting text processing pipeline")
            
            # Step 1: OCR/Text Extraction
            logger.info("Step 1: Text extraction")
            ocr_result = await ocr_service.extract_from_text(text)
            
            if ocr_result.status != "success":
                return ProcessingResponse(
                    status=ocr_result.status,
                    reason=ocr_result.reason,
                    raw_tokens=ocr_result.raw_tokens,
                    confidence=ocr_result.confidence
                )
            
            # Check if we have sufficient confidence to proceed
            if ocr_result.confidence < self.processing_threshold:
                return ProcessingResponse(
                    status="low_confidence",
                    reason=f"OCR confidence {ocr_result.confidence:.2f} below threshold {self.processing_threshold}",
                    raw_tokens=ocr_result.raw_tokens,
                    confidence=ocr_result.confidence
                )
            
            # Step 2: Normalization
            logger.info("Step 2: Amount normalization")
            normalization_result = await normalization_service.normalize_amounts(
                ocr_result.raw_tokens, 
                ocr_result.confidence
            )
            
            if not normalization_result.normalized_amounts:
                return ProcessingResponse(
                    status="no_amounts_found",
                    reason="No valid amounts found after normalization",
                    raw_tokens=ocr_result.raw_tokens,
                    confidence=ocr_result.confidence,
                    normalization_confidence=normalization_result.normalization_confidence
                )
            
            # Step 3: Classification
            logger.info("Step 3: Amount classification")
            classification_result = await classification_service.classify_amounts(
                normalization_result.normalized_amounts,
                text,
                ocr_result.currency_hint,
                "text"
            )
            
            # Step 4: Final Output Assembly
            logger.info("Step 4: Final output assembly")
            return await self._assemble_final_output(
                ocr_result,
                normalization_result,
                classification_result,
                text
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            return ProcessingResponse(
                status="error",
                reason=f"Pipeline processing error: {str(e)}",
                confidence=0.0
            )
    
    async def process_image(self, image_data: bytes) -> ProcessingResponse:
        """
        Process image input through the complete pipeline.
        
        Args:
            image_data: Image bytes to process
            
        Returns:
            ProcessingResponse with final results
        """
        try:
            logger.info("Starting image processing pipeline")
            
            # Step 1: OCR/Image Extraction
            logger.info("Step 1: OCR extraction from image")
            ocr_result = await ocr_service.extract_from_image(image_data)
            
            if ocr_result.status != "success":
                return ProcessingResponse(
                    status=ocr_result.status,
                    reason=ocr_result.reason,
                    raw_tokens=ocr_result.raw_tokens,
                    confidence=ocr_result.confidence
                )
            
            # Use the original OCR text if available, otherwise reconstruct from tokens
            extracted_text = ocr_result.original_text or self._reconstruct_text_from_tokens(ocr_result.raw_tokens)
            
            # Continue with text processing pipeline
            return await self._continue_pipeline_from_ocr(
                ocr_result,
                extracted_text
            )
            
        except Exception as e:
            logger.error(f"Image pipeline error: {str(e)}")
            return ProcessingResponse(
                status="error",
                reason=f"Image processing error: {str(e)}",
                confidence=0.0
            )
    
    async def _continue_pipeline_from_ocr(self, ocr_result, extracted_text: str) -> ProcessingResponse:
        """
        Continue pipeline processing from OCR results.
        
        Args:
            ocr_result: Results from OCR processing
            extracted_text: Reconstructed text for classification
            
        Returns:
            ProcessingResponse with final results
        """
        # Check confidence threshold
        if ocr_result.confidence < self.processing_threshold:
            return ProcessingResponse(
                status="low_confidence",
                reason=f"OCR confidence {ocr_result.confidence:.2f} below threshold {self.processing_threshold}",
                raw_tokens=ocr_result.raw_tokens,
                confidence=ocr_result.confidence
            )
        
        # Step 2: Normalization
        logger.info("Step 2: Amount normalization")
        normalization_result = await normalization_service.normalize_amounts(
            ocr_result.raw_tokens,
            ocr_result.confidence
        )
        
        if not normalization_result.normalized_amounts:
            return ProcessingResponse(
                status="no_amounts_found",
                reason="No valid amounts found after normalization",
                raw_tokens=ocr_result.raw_tokens,
                confidence=ocr_result.confidence,
                normalization_confidence=normalization_result.normalization_confidence
            )
        
        # Step 3: Classification
        logger.info("Step 3: Amount classification")
        classification_result = await classification_service.classify_amounts(
            normalization_result.normalized_amounts,
            extracted_text,
            ocr_result.currency_hint,
            "image"
        )
        
        # Step 4: Final Output Assembly
        logger.info("Step 4: Final output assembly")
        return await self._assemble_final_output(
            ocr_result,
            normalization_result,
            classification_result,
            extracted_text
        )
    
    def _reconstruct_text_from_tokens(self, tokens: list) -> str:
        """
        Reconstruct text from tokens for classification context.
        
        Args:
            tokens: List of extracted tokens
            
        Returns:
            Reconstructed text string
        """
        # Create a simple text representation
        # This is a fallback since we don't have the original OCR text
        reconstructed_parts = []
        
        for i, token in enumerate(tokens):
            if i == 0:
                reconstructed_parts.append(f"Total: {token}")
            elif i == 1:
                reconstructed_parts.append(f"Paid: {token}")
            elif i == 2:
                reconstructed_parts.append(f"Due: {token}")
            else:
                reconstructed_parts.append(f"Amount: {token}")
        
        return " | ".join(reconstructed_parts)
    
    async def _assemble_final_output(
        self,
        ocr_result,
        normalization_result,
        classification_result,
        original_text: str
    ) -> ProcessingResponse:
        """
        Assemble the final output from all pipeline stages.
        
        Args:
            ocr_result: OCR stage results
            normalization_result: Normalization stage results
            classification_result: Classification stage results
            original_text: Original input text
            
        Returns:
            Final ProcessingResponse
        """
        try:
            # Detect final currency
            currency, currency_confidence = currency_detector.detect_currency(original_text)
            final_currency = currency.value if currency.value != "UNKNOWN" else ocr_result.currency_hint
            
            # Calculate overall confidence
            confidences = [
                ocr_result.confidence,
                normalization_result.normalization_confidence,
                classification_result.confidence
            ]
            
            # Weight the confidences (OCR and normalization are more critical)
            weights = [0.4, 0.4, 0.2]
            overall_confidence = sum(c * w for c, w in zip(confidences, weights))
            
            # Validate final results
            valid_amounts = []
            for amount_item in classification_result.amounts:
                is_valid, _ = validation_utils.validate_amount_value(amount_item.value)
                if is_valid:
                    valid_amounts.append(amount_item)
                else:
                    logger.warning(f"Filtering out invalid amount: {amount_item.value}")
            
            if not valid_amounts:
                return ProcessingResponse(
                    status="no_amounts_found",
                    reason="No valid amounts remained after final validation",
                    raw_tokens=ocr_result.raw_tokens,
                    confidence=overall_confidence,
                    normalization_confidence=normalization_result.normalization_confidence,
                    classification_confidence=classification_result.confidence
                )
            
            # Final status determination
            if overall_confidence >= self.processing_threshold:
                status = "ok"
                reason = None
            else:
                status = "low_confidence"
                reason = f"Overall confidence {overall_confidence:.2f} below threshold"
            
            logger.info(f"Pipeline completed: {len(valid_amounts)} amounts, confidence {overall_confidence:.2f}")
            
            return ProcessingResponse(
                currency=final_currency,
                amounts=valid_amounts,
                status=status,
                confidence=overall_confidence,
                raw_tokens=ocr_result.raw_tokens,
                normalization_confidence=normalization_result.normalization_confidence,
                classification_confidence=classification_result.confidence,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error assembling final output: {str(e)}")
            return ProcessingResponse(
                status="error",
                reason=f"Final assembly error: {str(e)}",
                confidence=0.0
            )
    
    def get_pipeline_status(self) -> dict:
        """
        Get the current status of the pipeline.
        
        Returns:
            Dictionary with pipeline status information
        """
        return {
            "pipeline_version": "1.0.0",
            "processing_threshold": self.processing_threshold,
            "services_loaded": {
                "ocr_service": ocr_service is not None,
                "normalization_service": normalization_service is not None,
                "classification_service": classification_service is not None
            }
        }

# Global pipeline instance
pipeline = AmountDetectionPipeline()