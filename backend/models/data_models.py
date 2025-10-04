from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class AmountType(Enum):
    """Types of amounts that can be detected in medical documents."""
    # Standard financial types
    TOTAL_BILL = "total_bill"
    PAID = "paid"
    DUE = "due"
    BALANCE = "balance"
    DISCOUNT = "discount"
    TAX = "tax"
    COPAY = "copay"
    DEDUCTIBLE = "deductible"
    INSURANCE_COVERED = "insurance_covered"
    
    # Medical service types
    CONSULTATION = "consultation"
    X_RAY = "x_ray"
    MEDICINE = "medicine"
    BLOOD_TEST = "blood_test"
    ULTRASOUND = "ultrasound"
    SCAN = "scan"
    INJECTION = "injection"
    ECG = "ecg"
    NURSING = "nursing"
    PHYSIOTHERAPY = "physiotherapy"
    MRI = "mri"
    CT_SCAN = "ct_scan"
    PET_SCAN = "pet_scan"
    ENDOSCOPY = "endoscopy"
    BIOPSY = "biopsy"
    SURGERY = "surgery"
    LAB_TEST = "lab_test"
    PATHOLOGY = "pathology"
    RADIOLOGY = "radiology"
    
    # Fallback
    OTHER = "other"

class Currency(Enum):
    """Supported currencies."""
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    UNKNOWN = "UNKNOWN"

@dataclass
class RawToken:
    """Raw token extracted from text/OCR."""
    text: str
    position: int
    confidence: float
    context: str  # Surrounding text for context

@dataclass
class NormalizedAmount:
    """Normalized amount after OCR correction."""
    original_text: str
    normalized_value: float
    confidence: float
    corrections_made: List[str]

@dataclass
class ClassifiedAmount:
    """Amount with classification and context."""
    amount: NormalizedAmount
    type: AmountType
    confidence: float
    source_context: str
    position_in_text: int

@dataclass
class ProcessingResult:
    """Internal result structure for pipeline processing."""
    raw_tokens: List[RawToken]
    normalized_amounts: List[NormalizedAmount]
    classified_amounts: List[ClassifiedAmount]
    detected_currency: Currency
    overall_confidence: float
    processing_notes: List[str]