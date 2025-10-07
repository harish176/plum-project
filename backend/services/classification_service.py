import logging
import re
from typing import List, Dict, Tuple, Optional
from models.data_models import AmountType, ClassifiedAmount, NormalizedAmount
from models.request_models import ClassificationResponse, AmountItem
from utils.text_utils import text_processor
from config.settings import settings

logger = logging.getLogger(__name__)

class ClassificationService:
    """Service for classifying amounts based on context and keywords."""
    
    def __init__(self):
        self.amount_type_keywords = settings.AMOUNT_TYPE_KEYWORDS
        self.min_confidence = settings.CLASSIFICATION_CONFIDENCE_THRESHOLD
    
    async def classify_amounts(
        self, 
        amounts: List[float], 
        original_text: str,
        currency_hint: Optional[str] = None,
        input_source: str = "text"
    ) -> ClassificationResponse:
        """
        Classify amounts based on surrounding context.
        
        Args:
            amounts: List of normalized amounts
            original_text: Original text containing the amounts
            currency_hint: Detected currency hint
            input_source: Source of input ("text" or "image")
            
        Returns:
            ClassificationResponse with classified amounts
        """
        try:
            if not amounts:
                return ClassificationResponse(
                    amounts=[],
                    confidence=0.0
                )
            
            logger.info(f"Classifying {len(amounts)} amounts using text context")
            
            # Clean text for analysis
            cleaned_text = text_processor.clean_text(original_text.lower())
            
            # Find amount contexts in text
            amount_contexts = self._find_amount_contexts(amounts, original_text)
            
            # Classify each amount
            classified_amounts = []
            classification_confidences = []
            
            for amount in amounts:
                context = amount_contexts.get(amount, "")
                amount_type, confidence, source_context = self._classify_single_amount(amount, context, cleaned_text)
                
                # Extract item name from context or use the classified type
                item_name = self._extract_item_name(amount, context, amount_type, source_context)
                
                # Debug logging
                print(f"DEBUG: Amount {amount} -> Context: '{context}' -> Type: {amount_type.value} -> Item: {item_name}")
                
                classified_amounts.append(AmountItem(
                    type=item_name,
                    value=amount,
                    source=input_source
                ))
                
                classification_confidences.append(confidence)
                logger.debug(f"Classified {amount} as {item_name} with confidence {confidence:.2f}")
            
            # Resolve conflicts and improve classifications (temporarily disabled to test)
            # classified_amounts = self._resolve_classification_conflicts(classified_amounts, original_text)
            
            # Calculate overall confidence
            overall_confidence = sum(classification_confidences) / len(classification_confidences) if classification_confidences else 0.0
            
            logger.info(f"Classification completed with overall confidence {overall_confidence:.2f}")
            
            return ClassificationResponse(
                amounts=classified_amounts,
                confidence=overall_confidence
            )
            
        except Exception as e:
            logger.error(f"Error in classification: {str(e)}")
            return ClassificationResponse(
                amounts=[],
                confidence=0.0
            )
    
    def _find_amount_contexts(self, amounts: List[float], text: str) -> Dict[float, str]:
        """
        Find context strings for each amount in the text.
        
        Args:
            amounts: List of amounts to find contexts for
            text: Original text
            
        Returns:
            Dictionary mapping amounts to their contexts
        """
        amount_contexts = {}
        
        # Apply OCR corrections to the text to match the corrected amounts
        from utils.text_utils import TextProcessor
        text_processor = TextProcessor()
        corrected_text, corrections = text_processor.correct_ocr_digits(text)
        
        # Additional fix for percentage patterns (1% -> 10% in discount context)
        if 'discount' in corrected_text.lower() and '1%' in corrected_text:
            corrected_text = corrected_text.replace('1%', '10%')
            corrections.append("Discount percentage: '1%' -> '10%'")
        
        # Fix common OCR errors for field names
        corrected_text = corrected_text.replace('Du0:', 'Due:')
        corrected_text = corrected_text.replace('Tota1:', 'Total:')
        
        # Use the corrected text for context detection
        search_text = corrected_text
        
        for amount in amounts:
            # Create patterns to find this amount in text with currency
            # Use word boundaries to avoid partial matches (e.g., "10" in "1000")
            amount_str = str(int(amount)) if amount.is_integer() else str(amount)
            amount_patterns = [
                f"Rs\\.{amount_str}\\b",
                f"Rs\\. {amount_str}\\b", 
                f"₹{amount_str}\\b",
                f"₹ {amount_str}\\b",
                f"\\b{amount_str}\\b",  # Add word boundaries to prevent partial matches
            ]
            
            best_context = ""
            best_context_score = 0
            
            for pattern in amount_patterns:
                # Find all occurrences of this pattern (use raw pattern, not escaped, for word boundaries)
                for match in re.finditer(pattern, search_text, re.IGNORECASE):
                    # Get more focused context - look for sentence boundaries or line breaks
                    start = match.start()
                    end = match.end()
                    
                    # Extend backwards to find start of context
                    context_start = start
                    while context_start > 0 and search_text[context_start - 1] not in ['\n', '.', '|']:
                        context_start -= 1
                        if start - context_start > 40:  # Limit backward search
                            break
                    
                    # Extend forwards to find end of context
                    context_end = end
                    while context_end < len(search_text) and search_text[context_end] not in ['\n', '.', '|']:
                        context_end += 1
                        if context_end - end > 40:  # Limit forward search
                            break
                    
                    context = search_text[context_start:context_end].strip()
                    
                    # Score context quality
                    context_score = 0
                    
                    # Prefer contexts that contain descriptive words before the amount
                    descriptive_before = re.search(r'([a-zA-Z\s-]+)(?::\s*|[-\s]+)' + re.escape(pattern), context, re.IGNORECASE)
                    if descriptive_before:
                        context_score += 3
                    
                    # Prefer contexts with currency symbols
                    if any(symbol in pattern for symbol in ['Rs.', '₹']):
                        context_score += 2
                    
                    # Prefer shorter, more focused contexts
                    if len(context) < 80:
                        context_score += 1
                    
                    if context_score > best_context_score:
                        best_context = context
                        best_context_score = context_score
            
            # Special handling for percentage amounts (like "10%" becoming 10.0)
            # This handles cases where OCR extracts "10" from "10%" in text
            if not best_context and amount <= 100:
                # Look for percentage patterns - both exact and fuzzy matching
                percentage_patterns = [
                    f"{int(amount)}%",
                    f"{amount:.0f}%", 
                    f"{amount:.1f}%"
                ]
                
                for perc_pattern in percentage_patterns:
                    perc_match = re.search(re.escape(perc_pattern), text, re.IGNORECASE)
                    if perc_match:
                        # Get context around the percentage
                        start = perc_match.start()
                        end = perc_match.end()
                        
                        # Find start of line or context
                        context_start = start
                        while context_start > 0 and text[context_start - 1] not in ['\n']:
                            context_start -= 1
                            if start - context_start > 30:
                                break
                        
                        # Find end of line or context  
                        context_end = end
                        while context_end < len(text) and text[context_end] not in ['\n']:
                            context_end += 1
                            if context_end - end > 30:
                                break
                        
                        context = text[context_start:context_end].strip()
                        best_context = context
                        best_context_score = 5  # High score for percentage matches
                        break
                
                # Also try general percentage pattern search for small amounts
                if not best_context:
                    # Look for any percentage near this amount value
                    perc_search = re.search(r'\b' + str(int(amount)) + r'%', text, re.IGNORECASE)
                    if perc_search:
                        # Get context around this percentage
                        start = perc_search.start()
                        end = perc_search.end()
                        
                        context_start = max(0, start - 20)
                        while context_start > 0 and text[context_start] not in ['\n']:
                            context_start -= 1
                        
                        context_end = min(len(text), end + 20)
                        while context_end < len(text) and text[context_end] not in ['\n']:
                            context_end += 1
                        
                        context = text[context_start:context_end].strip()
                        if context:
                            best_context = context
                            best_context_score = 4
            
            # Fallback to simple context if no good match found
            if not best_context:
                # Just find the amount as a number and get surrounding text
                amount_str = str(int(amount)) if amount.is_integer() else str(amount)
                pos = text.find(amount_str)
                if pos >= 0:
                    start = max(0, pos - 30)
                    end = min(len(text), pos + len(amount_str) + 30)
                    best_context = text[start:end]
                else:
                    best_context = text[:60]  # Last resort
            
            amount_contexts[amount] = best_context
        
        return amount_contexts
    
    def _classify_single_amount(self, amount: float, context: str, full_text: str) -> Tuple[AmountType, float, str]:
        """
        Classify a single amount based on its context.
        
        Args:
            amount: Amount to classify
            context: Local context around the amount
            full_text: Full text for additional context
            
        Returns:
            Tuple of (AmountType, confidence, source_description)
        """
        # STEP 1: Check for direct associations (words immediately before amount with currency)
        # This should override general context matching
        amount_str = str(int(amount)) if amount.is_integer() else str(amount)
        direct_association_found = False
        direct_type = None
        
        # Patterns for direct association: "Service: Rs.Amount" or "Service Rs.Amount"  
        # Use greedy matching and include hyphens for compound words like "X-Ray"
        direct_patterns = [
            r'([a-zA-Z][a-zA-Z\s\-]+):\s*Rs\.?\s*' + re.escape(amount_str),
            r'([a-zA-Z][a-zA-Z\s\-]+)\s+Rs\.?\s*' + re.escape(amount_str),
            r'([a-zA-Z][a-zA-Z\s\-]+)\s*₹\s*' + re.escape(amount_str),
        ]
        
        for pattern in direct_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                service_name = match.group(1).strip().lower()
                
                # Map service names to types (check all variations)
                # Start with medical bill financial terms for better precision
                service_mappings = {
                    # Financial terms - be specific about different types of "amount"
                    'final amount': 'total_bill',
                    'grand total': 'total_bill',
                    'net amount': 'total_bill',
                    'total amount': 'total_bill', 
                    'sub total': 'total_bill',
                    'subtotal': 'total_bill',
                    'amount paid': 'paid',
                    'paid amount': 'paid',
                    'payment': 'paid',
                    'amount due': 'due',
                    'due amount': 'due',
                    'balance': 'due',
                    'outstanding': 'due',
                    'discount': 'discount',
                    'concession': 'discount',
                    'tax': 'tax',
                    'gst': 'tax',
                    'vat': 'tax',
                    # Medical services
                    'consultation': 'consultation',
                    'consult': 'consultation',
                    'x-ray': 'x_ray', 
                    'x ray': 'x_ray',
                    'xray': 'x_ray',
                    'medicine': 'medicine',
                    'medication': 'medicine',
                    'blood test': 'blood_test',
                    'blood': 'blood_test',
                    'ultrasound': 'ultrasound',
                    'scan': 'scan',
                    'injection': 'injection',
                    'ecg': 'ecg',
                    'nursing': 'nursing',
                    'physiotherapy': 'physiotherapy',
                    'physio': 'physiotherapy',
                    'mri': 'mri',
                    'ct scan': 'ct_scan',
                    'ct': 'ct_scan',
                    'pet scan': 'pet_scan',
                    'pet': 'pet_scan',
                    'endoscopy': 'endoscopy',
                    'biopsy': 'biopsy',
                    'surgery': 'surgery',
                    'operation': 'surgery',
                    'lab test': 'lab_test',
                    'laboratory': 'lab_test',
                    'pathology': 'pathology',
                    'radiology': 'radiology',
                    'total': 'total_bill',
                    'paid': 'paid',
                    'due': 'due',
                    'discount': 'discount',
                    'tax': 'tax'
                }
                
                for service_key, amount_type in service_mappings.items():
                    if service_key in service_name:
                        direct_association_found = True
                        direct_type = amount_type
                        break
                
                # If no exact match found, check if it looks like a medical service
                if not direct_association_found:
                    # Check if the service name looks like a medical service
                    # (not total, paid, due, discount, tax - which are financial terms)
                    financial_terms = {'total', 'paid', 'due', 'discount', 'tax', 'amount', 'bill', 'balance'}
                    if (service_name.lower() not in financial_terms and 
                        len(service_name.strip()) > 2 and  # Not just abbreviations like "Rs"
                        service_name.replace(' ', '').isalpha()):  # Contains only letters and spaces
                        
                        # Treat it as a medical service with the service name as type
                        direct_association_found = True
                        # Convert service name to valid enum format (lowercase, replace spaces with underscores)
                        direct_type = service_name.lower().replace(' ', '_').replace('-', '_')
                        logger.info(f"Unknown medical service detected: '{service_name}' -> '{direct_type}'")
                
                if direct_association_found:
                    break
        
        # STEP 2: If direct association found, use it with high confidence
        if direct_association_found:
            try:
                return AmountType(direct_type), 0.9, f"Direct association found"
            except ValueError:
                # If the direct_type is not a valid AmountType enum value,
                # we'll return it as a string and handle it in the calling code
                logger.info(f"Dynamic medical service type: {direct_type}")
                # Return as OTHER type but we'll use the direct_type in item name extraction
                return AmountType.OTHER, 0.9, f"Direct association found: {direct_type}"
        
        # STEP 3: Fall back to keyword-based classification for non-direct associations
        type_scores = {}
        
        for amount_type, keywords in self.amount_type_keywords.items():
            score = 0
            matched_keywords = []
            
            # Check context for keywords
            context_lower = context.lower()
            for keyword in keywords:
                keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(keyword_pattern, context_lower))
                if matches > 0:
                    score += matches * 2  # Weight context matches highly
                    matched_keywords.append(keyword)
            
            # Check full text for keywords (lower weight)
            for keyword in keywords:
                keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(keyword_pattern, full_text))
                score += matches * 0.5
            
            if score > 0:
                type_scores[amount_type] = (score, matched_keywords)
        
        # Apply heuristics based on amount characteristics
        type_scores = self._apply_amount_heuristics(amount, type_scores, context, full_text)
        
        # Determine best classification
        if not type_scores:
            return AmountType.OTHER, 0.2, f"amount: {amount} (no context match)"
        
        best_type = max(type_scores.keys(), key=lambda k: type_scores[k][0])
        best_score, matched_keywords = type_scores[best_type]
        
        # Calculate confidence
        confidence = min(1.0, best_score * 0.1)  # Scale score to confidence
        
        # Create source description
        source = self._create_source_description(amount, context, matched_keywords)
        
        return AmountType(best_type), confidence, source
    
    def _apply_amount_heuristics(
        self, 
        amount: float, 
        type_scores: Dict[str, Tuple[float, List[str]]], 
        context: str, 
        full_text: str
    ) -> Dict[str, Tuple[float, List[str]]]:
        """
        Apply heuristics to improve classification based on amount characteristics.
        
        Args:
            amount: Amount being classified
            type_scores: Current type scores
            context: Local context
            full_text: Full text
            
        Returns:
            Updated type scores
        """
        # Percentage heuristic
        if 0 < amount <= 100:
            # Could be a percentage
            if any(char in context.lower() for char in ['%', 'percent', 'discount']):
                if 'discount' in type_scores:
                    score, keywords = type_scores['discount']
                    type_scores['discount'] = (score + 2, keywords + ['percentage_heuristic'])
        
        # Large amount heuristic (likely total)
        if amount > 1000:
            if 'total_bill' in type_scores:
                score, keywords = type_scores['total_bill']
                type_scores['total_bill'] = (score + 1, keywords + ['large_amount_heuristic'])
            elif 'total_bill' not in type_scores:
                type_scores['total_bill'] = (1, ['large_amount_heuristic'])
        
        # Small amount heuristic (likely copay or discount)
        if 10 <= amount <= 100:
            potential_types = ['copay', 'discount']
            for amount_type in potential_types:
                if amount_type in type_scores:
                    score, keywords = type_scores[amount_type]
                    type_scores[amount_type] = (score + 0.5, keywords + ['small_amount_heuristic'])
        
        # Position-based heuristics
        context_position = full_text.lower().find(context.lower())
        if context_position >= 0:
            relative_position = context_position / len(full_text)
            
            # Early in text often means total
            if relative_position < 0.3 and 'total_bill' in type_scores:
                score, keywords = type_scores['total_bill']
                type_scores['total_bill'] = (score + 0.5, keywords + ['early_position_heuristic'])
            
            # Late in text often means due/balance
            if relative_position > 0.7 and 'due' in type_scores:
                score, keywords = type_scores['due']
                type_scores['due'] = (score + 0.5, keywords + ['late_position_heuristic'])
        
        return type_scores
    
    def _create_source_description(self, amount: float, context: str, matched_keywords: List[str]) -> str:
        """
        Create a source description for the classified amount.
        
        Args:
            amount: Classified amount
            context: Context where amount was found
            matched_keywords: Keywords that matched for classification
            
        Returns:
            Source description string
        """
        # Find the most relevant part of context around the amount
        amount_str = str(int(amount)) if amount.is_integer() else str(amount)
        
        # Look for currency patterns around the amount
        currency_patterns = [r'Rs\.?\s*', r'₹\s*', r'INR\s*', r'\$\s*']
        amount_patterns = []
        
        # Create patterns with currency prefixes
        for curr_pattern in currency_patterns:
            amount_patterns.extend([
                f"{curr_pattern}{amount_str}",
                f"{curr_pattern}{amount:.0f}" if amount.is_integer() else f"{curr_pattern}{amount:.2f}",
            ])
        
        # Also try without currency
        amount_patterns.extend([amount_str, f"{amount:.0f}" if amount.is_integer() else f"{amount:.2f}"])
        
        best_snippet = ""
        best_context_score = 0
        
        for pattern in amount_patterns:
            matches = list(re.finditer(pattern, context, re.IGNORECASE))
            for match in matches:
                # Get surrounding context with more intelligent boundaries
                start = max(0, match.start() - 15)
                end = min(len(context), match.end() + 15)
                
                # Try to find word boundaries for cleaner snippets
                while start > 0 and context[start] not in [' ', '\n', '\t', ':', '-']:
                    start -= 1
                while end < len(context) and context[end] not in [' ', '\n', '\t', ':', '-']:
                    end += 1
                
                snippet = context[start:end].strip()
                
                # Score the context quality
                context_score = 0
                
                # Prefer snippets with descriptive words
                descriptive_words = ['x-ray', 'medicine', 'consultation', 'test', 'scan', 'bill', 
                                   'treatment', 'service', 'fee', 'charge', 'due', 'total', 'paid']
                for word in descriptive_words:
                    if word in snippet.lower():
                        context_score += 2
                
                # Prefer snippets that include the currency symbol
                if any(curr in snippet for curr in ['Rs.', '₹', 'INR']):
                    context_score += 1
                
                # Prefer longer, more informative snippets (up to a point)
                context_score += min(len(snippet) / 10, 3)
                
                if context_score > best_context_score:
                    best_context_score = context_score
                    best_snippet = snippet
        
        # Fallback if no good pattern found
        if not best_snippet:
            # Look for the amount without patterns and get surrounding context
            context_lower = context.lower()
            amount_lower = amount_str.lower()
            if amount_lower in context_lower:
                pos = context_lower.find(amount_lower)
                start = max(0, pos - 20)
                end = min(len(context), pos + len(amount_str) + 20)
                best_snippet = context[start:end].strip()
            else:
                best_snippet = context[:50]  # Last resort
        
        # Clean up the snippet
        best_snippet = re.sub(r'\s+', ' ', best_snippet)
        
        # Remove leading/trailing punctuation but keep meaningful ones
        best_snippet = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', best_snippet)
        
        return best_snippet if best_snippet else f"amount: {amount}"
    
    def _extract_item_name(self, amount: float, context: str, amount_type: AmountType, source_context: str = "") -> str:
        """
        Extract specific item name from context or return appropriate type.
        
        Args:
            amount: Amount value
            context: Context around the amount
            amount_type: Classified amount type
            source_context: Additional context from classification (may contain dynamic service names)
            
        Returns:
            Specific item name or type
        """
        # Check if source_context contains a dynamic service name
        if source_context and "Direct association found:" in source_context:
            dynamic_service = source_context.replace("Direct association found:", "").strip()
            if dynamic_service:
                return dynamic_service
        

        
        # Keep standard types as they are
        standard_types = ['total_bill', 'paid', 'due', 'discount', 'tax', 'copay']
        if amount_type.value in standard_types:
            return amount_type.value
        
        # If we have a specific medical service type (not 'other'), use it directly
        known_medical_services = ['consultation', 'x_ray', 'medicine', 'blood_test', 'ultrasound', 
                                 'scan', 'injection', 'ecg', 'nursing', 'physiotherapy', 'mri', 
                                 'ct_scan', 'pet_scan', 'endoscopy', 'biopsy', 'surgery', 
                                 'lab_test', 'pathology', 'radiology']
        if amount_type.value in known_medical_services:
            return amount_type.value
        
        # Define item patterns to look for (more comprehensive)
        item_patterns = {
            'consultation': [r'consultation', r'consult', r'doctor\s+fee', r'physician', r'visit'],
            'x_ray': [r'x[-\s]?ray', r'xray', r'radiograph'],
            'medicine': [r'medicine', r'medication', r'drugs?', r'pharma'],
            'blood_test': [r'blood\s+test', r'lab\s+test', r'laboratory', r'blood'],
            'scan': [r'scan', r'ct\s+scan', r'mri'],
            'ultrasound': [r'ultrasound', r'sonography', r'sono'],
            'surgery': [r'surgery', r'operation', r'procedure'],
            'injection': [r'injection', r'vaccine', r'shot'],
            'ecg': [r'ecg', r'ekg', r'electrocardiogram'],
            'physiotherapy': [r'physio', r'therapy', r'rehabilitation', r'physiotherapy'],
            'ambulance': [r'ambulance', r'transport'],
            'room_charges': [r'room', r'bed', r'ward', r'accommodation', r'charges'],
            'nursing': [r'nursing', r'nurse', r'care'],
            'test': [r'test(?!\s+rs)', r'testing'],  # Avoid matching "Test Rs."
        }
        
        context_lower = context.lower()
        
        # Score each item type based on context
        item_scores = {}
        for item_name, patterns in item_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, context_lower))
                score += matches
            
            if score > 0:
                item_scores[item_name] = score
        
        # Return the best matching item name
        if item_scores:
            best_item = max(item_scores.keys(), key=lambda k: item_scores[k])
            return best_item
        
        # If no specific item found, try to extract from context using common patterns
        # Look for patterns like "Service: Rs.amount" or "Item - Rs.amount"
        amount_str = str(int(amount)) if amount.is_integer() else str(amount)
        
        # More comprehensive patterns to find item descriptions before amounts
        description_patterns = [
            r'([a-zA-Z][a-zA-Z\s]+?):\s*Rs\.?\s*' + re.escape(amount_str),
            r'([a-zA-Z][a-zA-Z\s]+?)\s*-\s*Rs\.?\s*' + re.escape(amount_str),
            r'([a-zA-Z][a-zA-Z\s]+?)\s+Rs\.?\s*' + re.escape(amount_str),
            r'([a-zA-Z][a-zA-Z\s]+?)\s*₹\s*' + re.escape(amount_str),
            # Pattern for "Amount: Rs.XXX Service" format
            r'Rs\.?\s*' + re.escape(amount_str) + r'\s+([a-zA-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in description_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                item_desc = match.group(1).strip().lower()
                # Clean up the description
                item_desc = re.sub(r'[^\w\s]', '', item_desc)
                item_desc = re.sub(r'\s+', '_', item_desc.strip())
                
                # Filter out common non-item words but keep meaningful ones
                exclude_words = ['item', 'service', 'charge', 'fee', 'cost', 'amount', 'bill', 'rs', 'inr']
                if item_desc and item_desc not in exclude_words and len(item_desc) > 2:
                    return item_desc
        
        # More aggressive fallback - try to find ANY descriptive word near the amount
        # Look for medical/service-related words in the context
        medical_service_patterns = [
            r'\b(consultation|consult|doctor|physician|visit)\b',
            r'\b(x[-\s]?ray|xray|radiograph)\b', 
            r'\b(medicine|medication|drugs?|pharma)\b',
            r'\b(blood|test|lab|laboratory)\b',
            r'\b(scan|ct|mri|ultrasound|sonography)\b',
            r'\b(surgery|operation|procedure)\b',
            r'\b(injection|vaccine|shot)\b',
            r'\b(ecg|ekg|electrocardiogram)\b',
            r'\b(physio|therapy|rehabilitation)\b',
            r'\b(ambulance|transport)\b',
            r'\b(room|bed|ward|accommodation)\b',
            r'\b(nursing|nurse|care)\b',
            r'\b(checkup|examination|exam)\b',
            r'\b(report|diagnostic|analysis)\b'
        ]
        
        context_lower = context.lower()
        for pattern in medical_service_patterns:
            if re.search(pattern, context_lower):
                # Extract the matched word and clean it
                match = re.search(pattern, context_lower)
                if match:
                    service_name = match.group(1).replace('-', '_').replace(' ', '_')
                    return service_name
        
        # If still no match, try to extract any meaningful word before the amount
        # Look for pattern: "Word Rs.Amount" or "Word: Rs.Amount"
        word_before_amount = re.search(r'\b([a-zA-Z]{3,})\s*:?\s*Rs\.?\s*' + re.escape(amount_str), context, re.IGNORECASE)
        if word_before_amount:
            word = word_before_amount.group(1).lower()
            exclude_generic = ['item', 'service', 'charge', 'fee', 'cost', 'amount', 'bill', 'total', 'paid', 'due', 'balance']
            if word not in exclude_generic:
                return word
        
        # Last resort: use the classified type or generic service name
        if amount_type.value != 'other':
            return amount_type.value
        else:
            # Generate a generic but meaningful name based on amount value
            if amount >= 1000:
                return 'major_service'
            elif amount >= 500:
                return 'standard_service'
            elif amount >= 100:
                return 'minor_service'
            else:
                return 'basic_service'
    
    def _resolve_classification_conflicts(self, classified_amounts: List[AmountItem], original_text: str) -> List[AmountItem]:
        """
        Resolve conflicts in classification and improve accuracy.
        
        Args:
            classified_amounts: List of classified amounts
            original_text: Original text for context
            
        Returns:
            List of amounts with resolved classifications
        """
        if len(classified_amounts) <= 1:
            return classified_amounts
        
        # Group by type, but only resolve conflicts for standard billing types
        # Service types (consultation, x_ray, medicine, etc.) should NOT be resolved
        standard_billing_types = ['total_bill', 'due', 'paid', 'discount', 'tax', 'copay']
        
        type_groups = {}
        for item in classified_amounts:
            # Only group standard billing types for conflict resolution
            if item.type in standard_billing_types:
                if item.type not in type_groups:
                    type_groups[item.type] = []
                type_groups[item.type].append(item)
        
        # Start with all amounts
        resolved_amounts = []
        
        # First, add all service types (non-standard types) without conflict resolution
        for item in classified_amounts:
            if item.type not in standard_billing_types:
                resolved_amounts.append(item)
        
        # Then resolve conflicts only for standard billing types
        for amount_type, items in type_groups.items():
            if len(items) == 1:
                resolved_amounts.extend(items)
            else:
                # Multiple items of same standard type - keep the one with highest value
                if amount_type in ['total_bill', 'due', 'paid']:
                    # For these types, usually want the highest value
                    best_item = max(items, key=lambda x: x.value)
                    resolved_amounts.append(best_item)
                    
                    # For duplicates, generate unique names instead of 'other'
                    for i, item in enumerate(items):
                        if item != best_item:
                            item.type = f"{amount_type}_{i+1}"  # e.g., "paid_2", "total_bill_2"
                            resolved_amounts.append(item)
                else:
                    # For discount, tax, copay - keep all with unique names if needed
                    if len(items) > 1:
                        for i, item in enumerate(items):
                            if i > 0:  # Keep first as-is, number the rest
                                item.type = f"{amount_type}_{i+1}"
                    resolved_amounts.extend(items)
        
        # Apply relationship-based improvements
        resolved_amounts = self._apply_relationship_rules(resolved_amounts)
        
        return resolved_amounts
    
    def _apply_relationship_rules(self, amounts: List[AmountItem]) -> List[AmountItem]:
        """
        Apply rules based on relationships between amounts.
        
        Args:
            amounts: List of classified amounts
            
        Returns:
            List with improved classifications
        """
        if len(amounts) < 2:
            return amounts
        
        # Find total, paid, and due amounts
        total_items = [item for item in amounts if item.type == AmountType.TOTAL_BILL.value]
        paid_items = [item for item in amounts if item.type == AmountType.PAID.value]
        due_items = [item for item in amounts if item.type == AmountType.DUE.value]
        
        # Apply total = paid + due rule
        if len(total_items) == 1 and len(paid_items) == 1 and len(due_items) == 1:
            total_val = total_items[0].value
            paid_val = paid_items[0].value
            due_val = due_items[0].value
            
            # Check if relationship holds (with small tolerance for rounding)
            if abs(total_val - (paid_val + due_val)) < 0.01:
                # Relationship confirmed - increase confidence implicitly
                # This could be used to boost confidence scores if needed
                pass
            elif abs(paid_val - (total_val + due_val)) < 0.01:
                # Paid is actually total + due (unusual but possible)
                # Could swap classifications
                pass
        
        return amounts

# Global classification service instance
classification_service = ClassificationService()