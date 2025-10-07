"""
Direct Extraction Service - Simple and reliable approach to extract medical bill amounts.
Instead of complex classification, directly extract and label amounts based on line patterns.
"""

import re
from typing import List, Dict, Optional, Tuple
from models.request_models import AmountItem
from utils.text_utils import TextProcessor
import logging

logger = logging.getLogger(__name__)

class DirectExtractionService:
    """Service for direct extraction of amounts from medical bills."""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        
        # Simple pattern mappings for common medical bill line types
        self.line_patterns = [
            # Order matters - more specific patterns first
            (r'\b(sub\s+total|subtotal)\b.*?(\d+\.?\d*)', "Sub Total"),
            (r'\b(grand\s+total|total\s+amount)\b.*?(\d+\.?\d*)', "Grand Total"),
            (r'\b(final\s+amount|net\s+amount)\b.*?(\d+\.?\d*)', "Final Amount"),
            (r'\b(amount\s+paid|paid\s+amount|payment)\b.*?(\d+\.?\d*)', "Amount Paid"),
            (r'\b(balance|balance\s+due|outstanding|due)\b.*?(\d+\.?\d*)', "Balance Due"),
            (r'\b(discount|concession|reduction)\b.*?(\d+\.?\d*)', "Discount"),
            (r'\b(tax|gst|vat|service\s+tax)\b.*?(\d+\.?\d*)', "Tax"),
            (r'\b(copay|co-pay|patient\s+share)\b.*?(\d+\.?\d*)', "Co-pay"),
            (r'\b(deductible|excess)\b.*?(\d+\.?\d*)', "Deductible"),
            (r'\b(insurance|covered|claim)\b.*?(\d+\.?\d*)', "Insurance"),
            (r'\b(consultation|consult)\b.*?(\d+\.?\d*)', "Consultation"),
            (r'\b(x-?ray|xray)\b.*?(\d+\.?\d*)', "X-Ray"),
            (r'\b(medicine|medication|drugs?)\b.*?(\d+\.?\d*)', "Medicine"),
            (r'\b(blood\s+test|blood)\b.*?(\d+\.?\d*)', "Blood Test"),
            (r'\b(ultrasound|scan)\b.*?(\d+\.?\d*)', "Scan"),
            (r'\b(injection|shot)\b.*?(\d+\.?\d*)', "Injection"),
            (r'\b(ecg|ekg)\b.*?(\d+\.?\d*)', "ECG"),
            (r'\b(mri)\b.*?(\d+\.?\d*)', "MRI"),
            (r'\b(ct\s+scan|ct)\b.*?(\d+\.?\d*)', "CT Scan"),
            (r'\b(total)\b.*?(\d+\.?\d*)', "Total"),  # Generic total - place near end
        ]
    
    def extract_from_text(self, text: str) -> List[AmountItem]:
        """
        Extract amounts directly from text using line-by-line pattern matching.
        
        Args:
            text: OCR text from medical bill
            
        Returns:
            List of AmountItem objects with direct extraction results
        """
        try:
            # Apply OCR corrections first
            corrected_text, corrections = self.text_processor.correct_ocr_digits(text)
            
            logger.info(f"Applied {len(corrections)} OCR corrections")
            
            # Split into lines and process each line
            lines = corrected_text.split('\n')
            extracted_amounts = []
            used_amounts = set()  # Avoid duplicates
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or not any(char.isdigit() for char in line):
                    continue
                
                # Try each pattern
                for pattern_regex, label in self.line_patterns:
                    match = re.search(pattern_regex, line, re.IGNORECASE)
                    if match:
                        try:
                            # Extract the amount (usually the last captured group)
                            amount_str = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                            amount = float(amount_str)
                            
                            # Create a unique key to avoid duplicates
                            amount_key = (label, amount)
                            if amount_key not in used_amounts:
                                extracted_amounts.append(AmountItem(
                                    type=label,
                                    value=amount,
                                    source=f"Line {line_num + 1}: {line}"
                                ))
                                used_amounts.add(amount_key)
                                logger.debug(f"Extracted {label}: ₹{amount} from '{line}'")
                                break  # Stop at first match for this line
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to extract amount from line: {line} - {e}")
                            continue
            
            logger.info(f"Direct extraction completed: {len(extracted_amounts)} amounts found")
            return extracted_amounts
            
        except Exception as e:
            logger.error(f"Error in direct extraction: {str(e)}")
            return []
    
    def extract_with_fallback(self, text: str) -> List[AmountItem]:
        """
        Extract amounts with fallback for unmatched lines containing numbers.
        
        Args:
            text: OCR text from medical bill
            
        Returns:
            List of AmountItem objects including fallback extractions
        """
        # First try direct pattern matching
        extracted_amounts = self.extract_from_text(text)
        
        # Fallback: find any remaining lines with amounts that weren't matched
        corrected_text, _ = self.text_processor.correct_ocr_digits(text)
        lines = corrected_text.split('\n')
        
        # Get already extracted amounts to avoid duplicates
        extracted_values = {item.value for item in extracted_amounts}
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or not any(char.isdigit() for char in line):
                continue
            
            # Find all amounts in this line
            amount_matches = re.findall(r'\b(\d+\.?\d*)\b', line)
            for amount_str in amount_matches:
                try:
                    amount = float(amount_str)
                    # Only include if it's a reasonable amount and not already extracted
                    if amount >= 1.0 and amount not in extracted_values:
                        extracted_amounts.append(AmountItem(
                            type="Other Amount",
                            value=amount,
                            source=f"Line {line_num + 1}: {line}"
                        ))
                        extracted_values.add(amount)
                        logger.debug(f"Fallback extraction: ₹{amount} from '{line}'")
                except ValueError:
                    continue
        
        return extracted_amounts
    
    def format_results(self, amounts: List[AmountItem]) -> Dict:
        """
        Format extraction results for API response.
        
        Args:
            amounts: List of extracted amounts
            
        Returns:
            Formatted dictionary for API response
        """
        return {
            "status": "success",
            "total_amounts_found": len(amounts),
            "amounts": [
                {
                    "label": item.type,
                    "value": item.value,
                    "currency": "INR",
                    "source_line": item.source
                }
                for item in amounts
            ],
            "extraction_method": "direct_pattern_matching"
        }