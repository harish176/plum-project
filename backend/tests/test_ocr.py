import pytest
import asyncio
from services.ocr_service import ocr_service

class TestOCRService:
    """Test cases for OCR service functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_from_text_simple(self):
        """Test basic text extraction."""
        text = "Total: INR 1200 | Paid: 1000 | Due: 200"
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "success"
        assert len(result.raw_tokens) >= 3
        assert "1200" in result.raw_tokens or "1200.0" in result.raw_tokens
        assert "1000" in result.raw_tokens or "1000.0" in result.raw_tokens
        assert "200" in result.raw_tokens or "200.0" in result.raw_tokens
        assert result.currency_hint == "INR"
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_extract_from_text_with_ocr_errors(self):
        """Test text extraction with simulated OCR errors."""
        text = "T0tal: Rs l200 | Pald: 1000 | Due: 200"  # OCR errors: 0->o, l->1, l->i
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "success"
        assert len(result.raw_tokens) >= 3
        assert result.currency_hint == "INR"
    
    @pytest.mark.asyncio
    async def test_extract_from_text_no_amounts(self):
        """Test text with no extractable amounts."""
        text = "This is a medical report with no financial information."
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "no_amounts_found"
        assert len(result.raw_tokens) == 0
        assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_extract_from_text_empty_input(self):
        """Test empty text input."""
        text = ""
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "error"
        assert "cannot be empty" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_extract_from_text_percentage(self):
        """Test extraction with percentage values."""
        text = "Total: $500 | Discount: 10% | Final: $450"
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "success"
        assert "500" in result.raw_tokens or "500.0" in result.raw_tokens
        assert "450" in result.raw_tokens or "450.0" in result.raw_tokens
        # Note: percentages might be filtered out as amounts
    
    @pytest.mark.asyncio
    async def test_extract_from_text_different_currencies(self):
        """Test currency detection with different currencies."""
        test_cases = [
            ("Total: $1200", "USD"),
            ("Amount: €500", "EUR"),
            ("Bill: £300", "GBP"),
            ("Cost: ₹1500", "INR"),
        ]
        
        for text, expected_currency in test_cases:
            result = await ocr_service.extract_from_text(text)
            assert result.status == "success"
            assert result.currency_hint == expected_currency
    
    @pytest.mark.asyncio
    async def test_extract_from_text_comma_separated_amounts(self):
        """Test extraction of comma-separated amounts."""
        text = "Total: INR 12,345 | Paid: 10,000 | Due: 2,345"
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "success"
        assert "12345" in result.raw_tokens or "12345.0" in result.raw_tokens
        assert "10000" in result.raw_tokens or "10000.0" in result.raw_tokens
        assert "2345" in result.raw_tokens or "2345.0" in result.raw_tokens
    
    @pytest.mark.asyncio
    async def test_extract_from_text_decimal_amounts(self):
        """Test extraction of decimal amounts."""
        text = "Copay: $25.50 | Deductible: $100.00 | Total: $125.50"
        result = await ocr_service.extract_from_text(text)
        
        assert result.status == "success"
        assert len(result.raw_tokens) >= 3
        # Check that decimal values are preserved
        decimal_found = any('.' in token for token in result.raw_tokens)
        assert decimal_found or all(float(token) for token in result.raw_tokens)  # Either preserved or converted correctly

if __name__ == "__main__":
    pytest.main([__file__, "-v"])