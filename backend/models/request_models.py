from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TextRequest(BaseModel):
    """Request model for text-based amount extraction."""
    text: str
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
            }
        }

class RawTokensResponse(BaseModel):
    """Response model for Step 1 - OCR/Text Extraction."""
    raw_tokens: List[str]
    currency_hint: Optional[str] = None
    confidence: float
    status: str = "success"
    reason: Optional[str] = None
    original_text: Optional[str] = None  # Preserve original OCR text for better source context

class NormalizationResponse(BaseModel):
    """Response model for Step 2 - Normalization."""
    normalized_amounts: List[float]
    normalization_confidence: float

class AmountItem(BaseModel):
    """Individual amount with type and value."""
    type: str
    value: float
    source: Optional[str] = None

class ClassificationResponse(BaseModel):
    """Response model for Step 3 - Classification."""
    amounts: List[AmountItem]
    confidence: float

class ProcessingResponse(BaseModel):
    """Final response model for the complete pipeline."""
    currency: Optional[str] = None
    amounts: List[AmountItem] = []
    status: str
    confidence: Optional[float] = None
    raw_tokens: Optional[List[str]] = None
    normalization_confidence: Optional[float] = None
    classification_confidence: Optional[float] = None
    reason: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "currency": "INR",
                "amounts": [
                    {"type": "total_bill", "value": 1200, "source": "text: 'Total: INR 1200'"},
                    {"type": "paid", "value": 1000, "source": "text: 'Paid: 1000'"},
                    {"type": "due", "value": 200, "source": "text: 'Due: 200'"}
                ],
                "status": "ok"
            }
        }

class CleanProcessingResponse(BaseModel):
    """Clean response model matching the exact desired output format."""
    currency: str
    amounts: List[AmountItem]
    status: str
    
    class Config:
        schema_extra = {
            "example": {
                "currency": "INR",
                "amounts": [
                    {"type": "total_bill", "value": 1200, "source": "text: 'Total: INR 1200'"},
                    {"type": "paid", "value": 1000, "source": "text: 'Paid: 1000'"},
                    {"type": "due", "value": 200, "source": "text: 'Due: 200'"}
                ],
                "status": "ok"
            }
        }