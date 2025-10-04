import pytest
import asyncio
from services.pipeline_service import AmountDetectionPipeline

class TestPipelineService:
    """Test cases for the complete pipeline integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = AmountDetectionPipeline()
    
    @pytest.mark.asyncio
    async def test_pipeline_text_processing_success(self):
        """Test successful end-to-end text processing."""
        text = "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
        result = await self.pipeline.process_text(text)
        
        assert result.status == "ok"
        assert result.currency == "INR"
        assert len(result.amounts) >= 3
        assert result.confidence > 0.5
        
        # Verify amount values
        values = [item.value for item in result.amounts]
        assert 1200.0 in values
        assert 1000.0 in values
        assert 200.0 in values
        
        # Verify types are assigned
        types = [item.type for item in result.amounts]
        assert "total_bill" in types
        assert "paid" in types
        assert "due" in types
    
    @pytest.mark.asyncio
    async def test_pipeline_text_processing_ocr_errors(self):
        """Test pipeline with OCR-like errors in text."""
        text = "T0tal: Rs l200 | Pald: I000 | Due: 2OO"
        result = await self.pipeline.process_text(text)
        
        # Should still succeed despite OCR errors
        assert result.status in ["ok", "low_confidence"]
        assert result.currency == "INR"
        assert len(result.amounts) >= 2  # Should extract some amounts
    
    @pytest.mark.asyncio
    async def test_pipeline_no_amounts_found(self):
        """Test pipeline with text containing no amounts."""
        text = "This is a medical report with patient information but no financial data."
        result = await self.pipeline.process_text(text)
        
        assert result.status == "no_amounts_found"
        assert len(result.amounts) == 0
        assert "no" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_low_confidence(self):
        """Test pipeline with low confidence input."""
        # Very ambiguous text
        text = "Some numbers: 123 456 789"
        result = await self.pipeline.process_text(text)
        
        # Should either succeed with low confidence or fail to find amounts
        assert result.status in ["ok", "low_confidence", "no_amounts_found"]
        if result.status == "low_confidence":
            assert result.confidence < 0.6
    
    @pytest.mark.asyncio
    async def test_pipeline_different_currencies(self):
        """Test pipeline with different currency formats."""
        test_cases = [
            ("Total: $1200 | Paid: $1000 | Due: $200", "USD"),
            ("Amount: €500 | Paid: €300 | Balance: €200", "EUR"),
            ("Bill: £800 | Paid: £600 | Due: £200", "GBP"),
            ("Cost: ₹1500 | Paid: ₹1000 | Due: ₹500", "INR"),
        ]
        
        for text, expected_currency in test_cases:
            result = await self.pipeline.process_text(text)
            assert result.status in ["ok", "low_confidence"]
            assert result.currency == expected_currency
            assert len(result.amounts) >= 3
    
    @pytest.mark.asyncio
    async def test_pipeline_complex_medical_bill(self):
        """Test pipeline with complex medical bill text."""
        text = """
        Medical Bill Summary
        Total Amount: $2,850.00
        Insurance Coverage: $2,280.00
        Patient Copay: $20.00
        Deductible: $550.00
        Amount Due: $570.00
        Discount Applied: 5%
        """
        result = await self.pipeline.process_text(text)
        
        assert result.status in ["ok", "low_confidence"]
        assert result.currency == "USD"
        assert len(result.amounts) >= 4
        
        # Check for expected amount types
        types = [item.type for item in result.amounts]
        expected_types = ["total_bill", "insurance_covered", "copay", "deductible", "due"]
        assert any(t in types for t in expected_types)
    
    @pytest.mark.asyncio
    async def test_pipeline_decimal_amounts(self):
        """Test pipeline with decimal amounts."""
        text = "Copay: $25.50 | Deductible: $150.75 | Total due: $176.25"
        result = await self.pipeline.process_text(text)
        
        assert result.status in ["ok", "low_confidence"]
        assert len(result.amounts) >= 3
        
        values = [item.value for item in result.amounts]
        assert 25.50 in values
        assert 150.75 in values
        assert 176.25 in values
    
    @pytest.mark.asyncio
    async def test_pipeline_comma_separated_amounts(self):
        """Test pipeline with comma-separated large amounts."""
        text = "Surgery total: $15,750 | Insurance paid: $12,600 | Patient owes: $3,150"
        result = await self.pipeline.process_text(text)
        
        assert result.status in ["ok", "low_confidence"]
        assert len(result.amounts) >= 3
        
        values = [item.value for item in result.amounts]
        assert 15750.0 in values
        assert 12600.0 in values
        assert 3150.0 in values
    
    @pytest.mark.asyncio
    async def test_pipeline_empty_input(self):
        """Test pipeline with empty input."""
        result = await self.pipeline.process_text("")
        
        assert result.status == "error"
        assert "empty" in result.reason.lower()
        assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_pipeline_very_long_text(self):
        """Test pipeline with very long input text."""
        # Create a long text with amounts scattered throughout
        long_text = "Patient visit summary. " * 100
        long_text += "Total charges: $500. "
        long_text += "Additional information. " * 100
        long_text += "Amount paid: $300. "
        long_text += "More details. " * 100
        long_text += "Balance due: $200."
        
        result = await self.pipeline.process_text(long_text)
        
        assert result.status in ["ok", "low_confidence"]
        assert len(result.amounts) >= 3
        
        values = [item.value for item in result.amounts]
        assert 500.0 in values
        assert 300.0 in values
        assert 200.0 in values
    
    @pytest.mark.asyncio
    async def test_pipeline_status(self):
        """Test pipeline status information."""
        status = self.pipeline.get_pipeline_status()
        
        assert "pipeline_version" in status
        assert "processing_threshold" in status
        assert "services_loaded" in status
        
        services = status["services_loaded"]
        assert services["ocr_service"]
        assert services["normalization_service"]
        assert services["classification_service"]
    
    @pytest.mark.asyncio
    async def test_pipeline_edge_case_amounts(self):
        """Test pipeline with edge case amounts."""
        text = "Very small copay: $0.01 | Large surgery: $99,999 | Regular visit: $150"
        result = await self.pipeline.process_text(text)
        
        # Should handle edge cases appropriately
        assert result.status in ["ok", "low_confidence", "no_amounts_found"]
        
        if result.amounts:
            values = [item.value for item in result.amounts]
            # Small amounts should be preserved if valid
            # Large amounts should be preserved if within limits
            assert all(0.01 <= v <= 1000000 for v in values)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])