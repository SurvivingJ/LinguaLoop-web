import json
from typing import Dict, List, Any, Optional

class QuestionValidator:
    """Validates question format and content"""
    
    @staticmethod
    def validate_question_format(question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize question structure
        
        Args:
            question_data: Raw question dict from API
            
        Returns:
            Validated question dict
            
        Raises:
            ValueError: If validation fails
        """
        required_fields = ["Question", "Answer", "Options"]
        
        # Check required fields exist
        for field in required_fields:
            if field not in question_data:
                raise ValueError(f"Missing required field: {field}")
        
        question = question_data["Question"].strip()
        answer = question_data["Answer"].strip()
        options = question_data["Options"]
        
        # Validate question text
        if not question or len(question) < 3:
            raise ValueError("Question text too short or empty")
        
        # Validate options
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError("Options must be a list of exactly 4 items")
        
        # Ensure all options are non-empty strings
        cleaned_options = []
        for i, option in enumerate(options):
            if not isinstance(option, str) or not option.strip():
                raise ValueError(f"Option {i+1} is empty or invalid")
            cleaned_options.append(option.strip())
        
        # Validate answer is in options
        if answer not in cleaned_options:
            if answer in ['A', 'B', 'C', 'D']:
                if answer == 'A':
                    answer = cleaned_options[0]
                elif answer == 'B':
                    answer = cleaned_options[1]
                elif answer == 'C':
                    answer = cleaned_options[2]
                elif answer == 'D':
                    answer = cleaned_options[3]
                else:
                    raise ValueError(f"Answer '{answer}' not found in options")
            else:
                raise ValueError(f"Answer '{answer}' not found in options")
        
        return {
            "Question": question,
            "Answer": answer,
            "Options": cleaned_options
        }
    
    @staticmethod
    def check_semantic_overlap(new_question: str, existing_questions: List[str], 
                              threshold: float = 0.7) -> bool:
        """
        Basic semantic overlap detection using keyword similarity
        
        Args:
            new_question: New question text
            existing_questions: List of existing question texts
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if overlap detected, False otherwise
        """
        if not existing_questions:
            return False
            
        new_words = set(new_question.lower().split())
        
        for existing in existing_questions:
            existing_words = set(existing.lower().split())
            
            # Calculate Jaccard similarity
            intersection = new_words.intersection(existing_words)
            union = new_words.union(existing_words)
            
            if len(union) > 0:
                similarity = len(intersection) / len(union)
                if similarity >= threshold:
                    return True
        
        return False
