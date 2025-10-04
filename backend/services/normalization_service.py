import logging
from typing import List, Tuple, Dict
from models.data_models import NormalizedAmount, RawToken
from models.request_models import NormalizationResponse
from utils.text_utils import text_processor
from utils.validation_utils import validation_utils
from config.settings import settings

logger = logging.getLogger(__name__)

class NormalizationService:
    """Service for normalizing extracted amounts and correcting OCR errors."""
    
    def __init__(self):
        self.min_confidence = settings.MIN_AMOUNT_CONFIDENCE
        self.correction_map = settings.OCR_DIGIT_CORRECTIONS
    
    async def normalize_amounts(self, raw_tokens: List[str], ocr_confidence: float = 1.0) -> NormalizationResponse:
        """
        Normalize raw tokens into proper numerical amounts.
        
        Args:
            raw_tokens: List of raw token strings
            ocr_confidence: Confidence from OCR process
            
        Returns:
            NormalizationResponse with normalized amounts
        """
        try:
            if not raw_tokens:
                return NormalizationResponse(
                    normalized_amounts=[],
                    normalization_confidence=0.0
                )
            
            logger.info(f"Normalizing {len(raw_tokens)} raw tokens")
            
            normalized_amounts = []
            normalization_scores = []
            
            for token in raw_tokens:
                try:
                    # Attempt to parse as float directly first
                    amount = float(token)
                    
                    # Validate the amount
                    is_valid, error_msg = validation_utils.validate_amount_value(amount)
                    if is_valid:
                        normalized_amounts.append(amount)
                        normalization_scores.append(0.9)  # High confidence for direct parsing
                        logger.debug(f"Successfully normalized token '{token}' to {amount}")
                    else:
                        logger.warning(f"Invalid amount {amount}: {error_msg}")
                
                except ValueError:
                    # Try more complex normalization
                    normalized_amount, confidence = self._complex_normalize(token)
                    if normalized_amount is not None:
                        normalized_amounts.append(normalized_amount)
                        normalization_scores.append(confidence)
                        logger.debug(f"Complex normalization: '{token}' -> {normalized_amount}")
                    else:
                        logger.warning(f"Failed to normalize token: '{token}'")
            
            # Calculate overall normalization confidence
            if normalization_scores:
                avg_normalization_confidence = sum(normalization_scores) / len(normalization_scores)
                # Factor in OCR confidence
                overall_confidence = (avg_normalization_confidence + ocr_confidence) / 2
            else:
                overall_confidence = 0.0
            
            logger.info(f"Normalized {len(normalized_amounts)} amounts with confidence {overall_confidence:.2f}")
            
            return NormalizationResponse(
                normalized_amounts=normalized_amounts,
                normalization_confidence=overall_confidence
            )
            
        except Exception as e:
            logger.error(f"Error in normalization: {str(e)}")
            return NormalizationResponse(
                normalized_amounts=[],
                normalization_confidence=0.0
            )
    
    def _complex_normalize(self, token: str) -> Tuple[float, float]:
        """
        Attempt complex normalization for problematic tokens.
        
        Args:
            token: Token to normalize
            
        Returns:
            Tuple of (normalized_amount, confidence) or (None, 0.0) if failed
        """
        try:
            # Apply OCR digit corrections
            corrected_token, corrections = self._apply_digit_corrections(token)
            
            # Try to extract amounts from corrected token
            amounts = text_processor.extract_amounts_from_token(corrected_token)
            
            if amounts:
                # Take the first valid amount
                amount = amounts[0]
                
                # Calculate confidence based on corrections made
                confidence = 0.7  # Base confidence
                if corrections:
                    # Lower confidence if corrections were needed
                    confidence -= len(corrections) * 0.1
                    confidence = max(0.1, confidence)  # Minimum confidence
                
                return amount, confidence
            
            # Try alternative parsing methods
            return self._fallback_parsing(token)
            
        except Exception as e:
            logger.debug(f"Complex normalization failed for '{token}': {str(e)}")
            return None, 0.0
    
    def _apply_digit_corrections(self, token: str) -> Tuple[str, List[str]]:
        """
        Apply OCR digit corrections to a token.
        
        Args:
            token: Token to correct
            
        Returns:
            Tuple of (corrected_token, list_of_corrections)
        """
        corrected = token
        corrections = []
        
        for wrong_char, correct_char in self.correction_map.items():
            if wrong_char in corrected:
                original = corrected
                corrected = corrected.replace(wrong_char, correct_char)
                if corrected != original:
                    corrections.append(f"'{wrong_char}' -> '{correct_char}'")
        
        return corrected, corrections
    
    def _fallback_parsing(self, token: str) -> Tuple[float, float]:
        """
        Fallback parsing methods for difficult tokens.
        
        Args:
            token: Token to parse
            
        Returns:
            Tuple of (amount, confidence) or (None, 0.0) if failed
        """
        try:
            # Method 1: Extract digits only
            digits_only = ''.join(c for c in token if c.isdigit() or c == '.')
            if digits_only and digits_only != '.':
                try:
                    amount = float(digits_only)
                    if validation_utils.validate_amount_value(amount)[0]:
                        return amount, 0.5  # Lower confidence for digits-only parsing
                except ValueError:
                    pass
            
            # Method 2: Try to parse parts of the token
            import re
            
            # Look for patterns like "1234.56" or "1,234"
            patterns = [
                r'\d+\.\d{1,2}',  # Decimal amounts
                r'\d{1,3}(?:,\d{3})*',  # Comma-separated thousands
                r'\d+'  # Simple integers
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, token)
                for match in matches:
                    try:
                        # Remove commas and parse
                        clean_match = match.replace(',', '')
                        amount = float(clean_match)
                        if validation_utils.validate_amount_value(amount)[0]:
                            return amount, 0.4  # Lower confidence for pattern matching
                    except ValueError:
                        continue
            
            return None, 0.0
            
        except Exception:
            return None, 0.0
    
    def validate_normalized_amounts(self, amounts: List[float]) -> List[float]:
        """
        Validate and filter normalized amounts.
        
        Args:
            amounts: List of amounts to validate
            
        Returns:
            List of valid amounts
        """
        valid_amounts = []
        
        for amount in amounts:
            is_valid, error_msg = validation_utils.validate_amount_value(amount)
            if is_valid:
                # Additional medical context validation
                if validation_utils.is_reasonable_medical_amount(amount):
                    valid_amounts.append(amount)
                else:
                    logger.warning(f"Amount {amount} seems unreasonable for medical context")
            else:
                logger.warning(f"Invalid amount {amount}: {error_msg}")
        
        return valid_amounts
    
    def detect_amount_relationships(self, amounts: List[float]) -> Dict[str, List[float]]:
        """
        Detect relationships between amounts (e.g., total = paid + due).
        
        Args:
            amounts: List of normalized amounts
            
        Returns:
            Dictionary of detected relationships
        """
        relationships = {
            "potential_totals": [],
            "potential_parts": [],
            "potential_percentages": []
        }
        
        if len(amounts) < 2:
            return relationships
        
        # Sort amounts for analysis
        sorted_amounts = sorted(amounts, reverse=True)
        
        # Look for total/parts relationships
        largest = sorted_amounts[0]
        others = sorted_amounts[1:]
        
        # Check if largest amount could be sum of others
        sum_others = sum(others)
        if abs(largest - sum_others) < 0.01:  # Allow for small rounding errors
            relationships["potential_totals"].append(largest)
            relationships["potential_parts"].extend(others)
        
        # Look for percentage-based amounts (amounts < 100 could be percentages)
        for amount in amounts:
            if amount < 100 and amount > 0:
                relationships["potential_percentages"].append(amount)
        
        return relationships

# Global normalization service instance
normalization_service = NormalizationService()