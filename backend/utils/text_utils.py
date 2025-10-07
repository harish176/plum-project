import re
from typing import List, Tuple, Optional
from config.settings import settings

class TextProcessor:
    """Utility class for text processing and cleaning."""
    
    def __init__(self):
        self.digit_correction_map = settings.OCR_DIGIT_CORRECTIONS
        self.numeric_pattern = re.compile(r'[\d,.\-\+\s]+')
        self.amount_pattern = re.compile(r'[\d,]+\.?\d*')
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize input text.
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might interfere with processing
        cleaned = re.sub(r'[^\w\s\.\,\-\+\$₹€£\(\)\|\:%]', ' ', cleaned)
        
        # Normalize common separators
        cleaned = cleaned.replace('|', ' | ')
        cleaned = cleaned.replace(':', ': ')
        
        return cleaned
    
    def extract_numeric_tokens(self, text: str) -> List[Tuple[str, int, str]]:
        """
        Extract numeric tokens from text with their positions and context.
        Enhanced to better handle OCR text patterns.
        
        Args:
            text: Input text
            
        Returns:
            List of tuples: (token, position, context)
        """
        tokens = []
        
        # Use multiple strategies to find numeric content
        
        # Strategy 1: Find currency-related patterns
        currency_patterns = [
            r'Rs\.?\s*\d+(?:\.\d+)?',      # Rs.100, Rs 100
            r'\d+(?:\.\d+)?\s*Rs',         # 100Rs, 100.50 Rs
            r'₹\s*\d+(?:\.\d+)?',          # ₹100
            r'\$\s*\d+(?:\.\d+)?',         # $100
        ]
        
        for pattern in currency_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                token = match.group().strip()
                position = match.start()
                context = self._get_context(text, position, match.end())
                tokens.append((token, position, context))
        
        # Strategy 2: Find standalone numbers
        number_patterns = [
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d{1,3})?\b',  # 1,234.56
            r'\b\d+(?:\.\d{1,3})?\b',                  # 123.45
            r'(?<!\d)\.\d{1,3}\b',                     # .30
        ]
        
        for pattern in number_patterns:
            for match in re.finditer(pattern, text):
                token = match.group().strip()
                # Skip very small numbers that are likely not amounts
                if len(token) > 0:
                    try:
                        value = float(token.replace(',', '') if not token.startswith('.') else '0' + token.replace(',', ''))
                        if value >= 1.0:  # Only consider numbers >= 1
                            position = match.start()
                            context = self._get_context(text, position, match.end())
                            tokens.append((token, position, context))
                    except ValueError:
                        continue
        
        # Strategy 3: Look for percentage values
        percentage_pattern = r'\d+(?:\.\d+)?%'
        for match in re.finditer(percentage_pattern, text):
            token = match.group().strip()
            position = match.start()
            context = self._get_context(text, position, match.end())
            tokens.append((token, position, context))
        
        # Remove duplicates by position, preferring longer/more specific tokens
        unique_tokens = []
        position_groups = {}
        
        # Group tokens by approximate position
        for token, position, context in tokens:
            position_key = (position // 5) * 5
            if position_key not in position_groups:
                position_groups[position_key] = []
            position_groups[position_key].append((token, position, context))
        
        # For each position group, select the best token
        for position_key, group_tokens in position_groups.items():
            if len(group_tokens) == 1:
                unique_tokens.append(group_tokens[0])
            else:
                # Prefer tokens with special characters (%, $, Rs, etc.) over plain numbers
                special_tokens = [(t, p, c) for t, p, c in group_tokens if any(char in t for char in ['%', '$', '₹', 'Rs'])]
                if special_tokens:
                    # Among special tokens, prefer the longest
                    best_token = max(special_tokens, key=lambda x: len(x[0]))
                    unique_tokens.append(best_token)
                else:
                    # Among plain numbers, prefer the longest
                    best_token = max(group_tokens, key=lambda x: len(x[0]))
                    unique_tokens.append(best_token)
        
        return unique_tokens
    
    def _get_context(self, text: str, start: int, end: int, window: int = 20) -> str:
        """Get context around a text position."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def correct_ocr_digits(self, text: str) -> Tuple[str, List[str]]:
        """
        Correct common OCR digit recognition errors.
        
        Args:
            text: Text with potential OCR errors
            
        Returns:
            Tuple of (corrected_text, list_of_corrections_made)
        """
        corrected = text
        corrections = []
        
        # First pass: correct obvious currency amount patterns
        currency_patterns = [
            # Handle patterns like Rs.150@ where @ represents 00
            (r'Rs\.(\d+)[@]+', lambda m: f"Rs.{m.group(1)}00"),
            # Handle patterns like Rs.1¢0, Rs.8@0, etc.
            (r'Rs\.([lIoOsSbBgGzZ¢@ec]\d+)', lambda m: f"Rs.{self._correct_amount_string(m.group(1))}"),
            (r'Rs\.(\d*[lIoOsSbBgGzZ¢@ec]+\d*)', lambda m: f"Rs.{self._correct_amount_string(m.group(1))}"),
            (r'Rs\.(\d+[lIoOsSbBgGzZ¢@ec]+)', lambda m: f"Rs.{self._correct_amount_string(m.group(1))}"),
            # Same for ₹ symbol
            (r'₹(\d+)[@]+', lambda m: f"₹{m.group(1)}00"),
            (r'₹([lIoOsSbBgGzZ¢@ec]\d+)', lambda m: f"₹{self._correct_amount_string(m.group(1))}"),
            (r'₹(\d*[lIoOsSbBgGzZ¢@ec]+\d*)', lambda m: f"₹{self._correct_amount_string(m.group(1))}"),
            (r'₹(\d+[lIoOsSbBgGzZ¢@ec]+)', lambda m: f"₹{self._correct_amount_string(m.group(1))}"),
        ]
        
        for pattern, replacement in currency_patterns:
            matches = list(re.finditer(pattern, corrected))
            for match in reversed(matches):  # Process from end to avoid index issues
                original = match.group()
                new_value = replacement(match)
                if original != new_value:
                    corrected = corrected[:match.start()] + new_value + corrected[match.end():]
                    corrections.append(f"Currency amount: '{original}' -> '{new_value}'")
        
        # Second pass: general digit corrections in numeric contexts (do this BEFORE word corrections)
        for wrong_char, correct_char in self.digit_correction_map.items():
            if wrong_char in corrected:
                # Only correct if it's in a numeric context
                pattern = rf'\b\w*{re.escape(wrong_char)}\w*\b'
                matches = list(re.finditer(pattern, corrected))
                
                # Process matches in reverse order to avoid index issues
                for match in reversed(matches):
                    word = match.group()
                    # Check if the word looks like it should be numeric
                    if self._looks_numeric(word):
                        corrected_word = word.replace(wrong_char, correct_char)
                        corrected = corrected[:match.start()] + corrected_word + corrected[match.end():]
                        corrections.append(f"'{wrong_char}' -> '{correct_char}' in '{word}'")
        
        # Third pass: word-level OCR corrections for common medical bill terms
        word_corrections = [
            (r'\bAm0unt\b', 'Amount'),
            (r'\bam0unt\b', 'amount'),
            (r'\bT0tal\b', 'Total'),
            (r'\bt0tal\b', 'total'),
            (r'\bBa1ance\b', 'Balance'),
            (r'\bba1ance\b', 'balance'),
            (r'\bFina1\b', 'Final'),
            (r'\bfina1\b', 'final'),
            (r'\bPa1d\b', 'Paid'),
            (r'\bpa1d\b', 'paid'),
            (r'\bD1scount\b', 'Discount'),
            (r'\bd1scount\b', 'discount'),
        ]
        
        for pattern, replacement in word_corrections:
            if re.search(pattern, corrected):
                old_text = corrected
                corrected = re.sub(pattern, replacement, corrected)
                if old_text != corrected:
                    corrections.append(f"Word correction: '{pattern}' -> '{replacement}'")
        
        return corrected, corrections
    
    def _correct_amount_string(self, amount_str: str) -> str:
        """Correct OCR errors in an amount string"""
        corrected = amount_str
        for wrong_char, correct_char in self.digit_correction_map.items():
            corrected = corrected.replace(wrong_char, correct_char)
        return corrected
    
    def _looks_numeric(self, word: str) -> bool:
        """
        Check if a word looks like it should be numeric.
        
        Args:
            word: Word to check
            
        Returns:
            True if word appears to be intended as numeric
        """
        # Don't correct currency symbols
        if word.lower() in ['rs', 'inr', 'usd', 'eur', 'gbp']:
            return False
        
        # Don't correct common words that might contain s, o, etc.
        common_words = ['total', 'hospital', 'patient', 'discount', 'consultation']
        if word.lower() in common_words:
            return False
        
        # Count digits vs letters
        digits = sum(1 for c in word if c.isdigit())
        letters = sum(1 for c in word if c.isalpha())
        
        # If mostly digits, or has currency context, likely numeric
        if digits > letters:
            return True
        
        # Check for currency or amount keywords nearby
        amount_indicators = ['rs', 'inr', 'usd', 'total', 'amount', 'paid', 'due']
        word_lower = word.lower()
        
        return any(indicator in word_lower for indicator in amount_indicators)
    
    def extract_amounts_from_token(self, token: str) -> List[float]:
        """
        Extract numerical amounts from a token.
        Enhanced to handle OCR text with mixed content and avoid spurious decimals.
        
        Args:
            token: Token to process
            
        Returns:
            List of extracted amounts
        """
        amounts = []
        
        # Handle currency tokens specifically (Rs.100, $50, etc.)
        if re.search(r'(Rs\.?|₹|\$|€|£)', token, re.IGNORECASE):
            # Extract the number part from currency tokens
            currency_patterns = [
                r'(Rs\.?|₹|\$|€|£)\s*(\d{1,6}(?:\.\d{1,2})?)',  # Rs.100, $50.25
                r'(\d{1,6}(?:\.\d{1,2})?)\s*(Rs\.?|₹|\$|€|£)',  # 100Rs, 50.25$
            ]
            
            for pattern in currency_patterns:
                matches = re.finditer(pattern, token, re.IGNORECASE)
                for match in matches:
                    # Extract the numeric part (group 2 for first pattern, group 1 for second)
                    number_str = match.group(2) if match.group(2).replace('.', '').isdigit() else match.group(1)
                    
                    try:
                        amount = float(number_str)
                        if 1.0 <= amount <= settings.MAX_AMOUNT_VALUE:  # Reasonable range for medical bills
                            amounts.append(amount)
                    except (ValueError, AttributeError):
                        continue
        
        # Handle percentage tokens (10%, 5.5%)
        elif '%' in token:
            percentage_match = re.search(r'(\d{1,3}(?:\.\d{1,2})?)\s*%', token)
            if percentage_match:
                try:
                    amount = float(percentage_match.group(1))
                    if 0.1 <= amount <= 100:  # Reasonable percentage range
                        amounts.append(amount)
                except ValueError:
                    pass
        
        # Handle standalone numbers (but be more restrictive)
        else:
            # Look for standalone numbers that could be amounts
            number_patterns = [
                r'\b\d{2,6}(?:\.\d{1,2})?\b',      # 10-999999.99 (avoid single digits)
                r'\b\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\b'  # 1,000 or 1,000.50
            ]
            
            for pattern in number_patterns:
                matches = re.finditer(pattern, token)
                for match in matches:
                    number_str = match.group()
                    
                    try:
                        cleaned = number_str.replace(',', '')
                        amount = float(cleaned)
                        
                        # Only include reasonable amounts (avoid tiny decimals)
                        if 1.0 <= amount <= settings.MAX_AMOUNT_VALUE:
                            amounts.append(amount)
                            
                    except ValueError:
                        continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_amounts = []
        for amount in amounts:
            if amount not in seen:
                seen.add(amount)
                unique_amounts.append(amount)
        
        return unique_amounts
    
    def get_surrounding_context(self, text: str, position: int, window: int = 30) -> str:
        """
        Get surrounding context for a position in text.
        
        Args:
            text: Full text
            position: Position to get context for
            window: Number of characters before and after
            
        Returns:
            Context string
        """
        start = max(0, position - window)
        end = min(len(text), position + window)
        return text[start:end].strip()

# Global text processor instance
text_processor = TextProcessor()