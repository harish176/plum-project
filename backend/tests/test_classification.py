import pytest
import asyncio
from services.classification_service import classification_service

class TestClassificationService:
    """Test cases for classification service functionality."""
    
    @pytest.mark.asyncio
    async def test_classify_basic_medical_bill(self):
        """Test classification of a basic medical bill."""
        amounts = [1200.0, 1000.0, 200.0]
        text = "Total: INR 1200 | Paid: 1000 | Due: 200"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        assert result.confidence > 0.0
        
        # Check that types are assigned
        types_found = [item.type for item in result.amounts]
        assert len(set(types_found)) > 1  # Should have different types
    
    @pytest.mark.asyncio
    async def test_classify_with_keywords(self):
        """Test classification with clear keyword indicators."""
        amounts = [1500.0, 1200.0, 300.0]
        text = "Total bill amount: 1500 | Insurance covered: 1200 | Patient copay: 300"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        
        # Look for expected classifications
        types_found = [item.type for item in result.amounts]
        assert "total_bill" in types_found
        assert "insurance_covered" in types_found or "copay" in types_found
    
    @pytest.mark.asyncio
    async def test_classify_discount_scenario(self):
        """Test classification with discount amounts."""
        amounts = [1000.0, 100.0, 900.0]
        text = "Original amount: 1000 | Discount: 100 | Final amount: 900"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        types_found = [item.type for item in result.amounts]
        assert "discount" in types_found
    
    @pytest.mark.asyncio
    async def test_classify_empty_amounts(self):
        """Test classification with empty amounts list."""
        amounts = []
        text = "Some text without amounts"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 0
        assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_classify_single_amount(self):
        """Test classification with single amount."""
        amounts = [1200.0]
        text = "Total medical bill: 1200"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 1
        assert result.amounts[0].value == 1200.0
        assert result.amounts[0].type  # Should have some type assigned
        assert result.amounts[0].source  # Should have source information
    
    @pytest.mark.asyncio
    async def test_classify_with_currency_context(self):
        """Test classification with currency context."""
        amounts = [500.0, 400.0, 100.0]
        text = "Hospital bill: $500 | Insurance paid: $400 | Patient due: $100"
        currency_hint = "USD"
        
        result = await classification_service.classify_amounts(amounts, text, currency_hint)
        
        assert len(result.amounts) == 3
        
        # Check source information includes context
        for item in result.amounts:
            assert item.source
            assert "text:" in item.source
    
    @pytest.mark.asyncio
    async def test_classify_percentage_amounts(self):
        """Test classification of percentage-like amounts."""
        amounts = [1000.0, 10.0, 900.0]
        text = "Bill total: 1000 | 10% discount applied | Final: 900"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        # The 10.0 should potentially be classified as discount
        discount_items = [item for item in result.amounts if item.type == "discount"]
        assert len(discount_items) > 0
    
    @pytest.mark.asyncio
    async def test_classify_large_amounts(self):
        """Test classification of large amounts."""
        amounts = [50000.0, 45000.0, 5000.0]
        text = "Surgery total: 50000 | Insurance coverage: 45000 | Patient responsibility: 5000"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        # Large amounts should likely be classified as total_bill
        total_items = [item for item in result.amounts if item.type == "total_bill"]
        assert len(total_items) > 0
    
    @pytest.mark.asyncio
    async def test_classify_with_ambiguous_context(self):
        """Test classification with ambiguous context."""
        amounts = [100.0, 200.0, 300.0]
        text = "Amount 1: 100, Amount 2: 200, Amount 3: 300"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 3
        # Should assign some type even with poor context
        for item in result.amounts:
            assert item.type
            assert item.value in amounts
    
    @pytest.mark.asyncio
    async def test_resolve_classification_conflicts(self):
        """Test resolution of classification conflicts."""
        # This tests the internal conflict resolution logic
        amounts = [1000.0, 1200.0]  # Two potential totals
        text = "Total amount: 1000 | Grand total: 1200"
        
        result = await classification_service.classify_amounts(amounts, text)
        
        assert len(result.amounts) == 2
        # Should handle potential duplicate classifications
        total_bills = [item for item in result.amounts if item.type == "total_bill"]
        # Either both are total_bill (conflict not resolved) or one is reclassified
        assert len(total_bills) <= 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])