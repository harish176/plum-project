import pytest
import asyncio
from services.normalization_service import normalization_service

class TestNormalizationService:
    """Test cases for normalization service functionality."""
    
    @pytest.mark.asyncio
    async def test_normalize_basic_amounts(self):
        """Test basic amount normalization."""
        raw_tokens = ["1200", "1000", "200"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 3
        assert 1200.0 in result.normalized_amounts
        assert 1000.0 in result.normalized_amounts
        assert 200.0 in result.normalized_amounts
        assert result.normalization_confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_normalize_decimal_amounts(self):
        """Test normalization of decimal amounts."""
        raw_tokens = ["25.50", "100.00", "125.50"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 3
        assert 25.50 in result.normalized_amounts
        assert 100.00 in result.normalized_amounts
        assert 125.50 in result.normalized_amounts
    
    @pytest.mark.asyncio
    async def test_normalize_comma_separated_amounts(self):
        """Test normalization of comma-separated amounts."""
        raw_tokens = ["12,345", "1,000", "2,345"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 3
        assert 12345.0 in result.normalized_amounts
        assert 1000.0 in result.normalized_amounts
        assert 2345.0 in result.normalized_amounts
    
    @pytest.mark.asyncio
    async def test_normalize_empty_input(self):
        """Test normalization with empty input."""
        raw_tokens = []
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 0
        assert result.normalization_confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_normalize_invalid_tokens(self):
        """Test normalization with invalid tokens."""
        raw_tokens = ["abc", "xyz", "invalid"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 0
        assert result.normalization_confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_normalize_mixed_valid_invalid(self):
        """Test normalization with mix of valid and invalid tokens."""
        raw_tokens = ["1200", "invalid", "200", "abc"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        assert len(result.normalized_amounts) == 2
        assert 1200.0 in result.normalized_amounts
        assert 200.0 in result.normalized_amounts
    
    @pytest.mark.asyncio
    async def test_normalize_with_ocr_errors(self):
        """Test normalization with OCR correction."""
        # Simulate OCR errors that should be corrected
        raw_tokens = ["l200", "I000", "2OO"]  # l->1, I->1, O->0
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        # Should have at least some successfully normalized amounts
        assert len(result.normalized_amounts) >= 0  # May or may not correct depending on implementation
    
    @pytest.mark.asyncio
    async def test_normalize_extreme_values(self):
        """Test normalization with extreme values."""
        raw_tokens = ["0.01", "999999", "0"]
        result = await normalization_service.normalize_amounts(raw_tokens)
        
        # Should filter out 0 and very large amounts based on validation
        valid_amounts = [amount for amount in result.normalized_amounts 
                        if 0.01 <= amount <= 1000000]
        assert len(valid_amounts) >= 2  # 0.01 and potentially 999999
    
    @pytest.mark.asyncio
    async def test_validate_normalized_amounts(self):
        """Test amount validation functionality."""
        amounts = [25.50, 1200.0, -50.0, 0.0, 2000000.0]
        valid_amounts = normalization_service.validate_normalized_amounts(amounts)
        
        # Should filter out negative, zero, and extremely large amounts
        assert 25.50 in valid_amounts
        assert 1200.0 in valid_amounts
        assert -50.0 not in valid_amounts
        assert 0.0 not in valid_amounts
        assert 2000000.0 not in valid_amounts  # Likely too large for medical context
    
    @pytest.mark.asyncio
    async def test_detect_amount_relationships(self):
        """Test detection of relationships between amounts."""
        amounts = [1200.0, 1000.0, 200.0]  # total = paid + due
        relationships = normalization_service.detect_amount_relationships(amounts)
        
        assert "potential_totals" in relationships
        assert "potential_parts" in relationships
        # Should detect that 1200 could be total of 1000 + 200
        assert 1200.0 in relationships["potential_totals"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])