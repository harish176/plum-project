import re
from typing import List, Optional, Tuple
from models.data_models import Currency
from config.settings import settings

class CurrencyDetector:
    """Utility class for detecting and handling currencies."""
    
    def __init__(self):
        self.currency_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict:
        """Compile regex patterns for each currency."""
        compiled = {}
        for currency, patterns in settings.CURRENCY_PATTERNS.items():
            compiled[currency] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def detect_currency(self, text: str) -> Tuple[Currency, float]:
        """
        Detect currency from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Tuple of (Currency, confidence_score)
        """
        currency_scores = {}
        
        for currency, patterns in self.currency_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                score += len(matches) * 0.3  # Weight per match
                
                # Bonus for early occurrence
                match = pattern.search(text)
                if match:
                    position_bonus = max(0, 1 - (match.start() / len(text)))
                    score += position_bonus * 0.2
            
            if score > 0:
                currency_scores[currency] = score
        
        if not currency_scores:
            return Currency.UNKNOWN, 0.0
        
        best_currency = max(currency_scores.items(), key=lambda x: x[1])
        confidence = min(1.0, best_currency[1])
        
        return Currency(best_currency[0]), confidence
    
    def extract_currency_context(self, text: str, currency: Currency) -> List[str]:
        """
        Extract text contexts where currency symbols appear.
        
        Args:
            text: Input text
            currency: Detected currency
            
        Returns:
            List of context strings around currency mentions
        """
        if currency == Currency.UNKNOWN:
            return []
        
        contexts = []
        patterns = self.currency_patterns.get(currency.value, [])
        
        for pattern in patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end].strip()
                contexts.append(context)
        
        return contexts
    
    def normalize_currency_symbol(self, text: str, target_currency: Currency) -> str:
        """
        Normalize currency symbols in text to a standard format.
        
        Args:
            text: Input text
            target_currency: Target currency to normalize to
            
        Returns:
            Text with normalized currency symbols
        """
        if target_currency == Currency.UNKNOWN:
            return text
        
        # Standard symbols for each currency
        standard_symbols = {
            Currency.INR: "₹",
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£"
        }
        
        standard_symbol = standard_symbols.get(target_currency, target_currency.value)
        
        # Replace all currency patterns with standard symbol
        patterns = self.currency_patterns.get(target_currency.value, [])
        result = text
        
        for pattern in patterns:
            result = pattern.sub(standard_symbol, result)
        
        return result

# Global currency detector instance
currency_detector = CurrencyDetector()