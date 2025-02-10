import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize_whitespace(text):
    """
    Normalize whitespace in the text while preserving paragraph breaks.
    - Replace multiple spaces with a single space
    - Preserve double line breaks (paragraph breaks)
    - Remove single line breaks within paragraphs
    """
    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)
    # Preserve double line breaks (paragraph breaks)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Remove single line breaks within paragraphs
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return text.strip()

def preprocess_text(text):
    """
    Preprocess the input text by performing minimal cleaning:
    1. Normalize whitespace while preserving paragraph structure
    2. Optionally, convert to lowercase (commented out by default)
    
    :param text: The input text to preprocess
    :return: The preprocessed text
    """
    try:
        logger.info("Starting text preprocessing")
        
        # Normalize whitespace
        text = normalize_whitespace(text)
        logger.debug("Whitespace normalized")
        
        # Optionally, convert to lowercase
        # Commented out by default to preserve original case
        # text = text.lower()
        # logger.debug("Text converted to lowercase")
        
        logger.info("Text preprocessing completed successfully")
        return text
    except Exception as e:
        logger.error(f"Error during text preprocessing: {str(e)}")
        raise

def split_into_sentences(text):
    """
    Split the text into sentences using a simple rule-based approach.
    This is a basic implementation and may not cover all cases perfectly.
    
    :param text: The input text to split into sentences
    :return: A list of sentences
    """
    # Split on period, exclamation mark, or question mark followed by a space and uppercase letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return sentences

def split_into_paragraphs(text):
    """
    Split the text into paragraphs.
    
    :param text: The input text to split into paragraphs
    :return: A list of paragraphs
    """
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def split_by_markdown_headings(text, level=1):
    """
    Split the text by markdown headings of the specified level.
    
    Args:
    text (str): The markdown text to split.
    level (int): The heading level to split by (default is 1 for top-level headings).
    
    Returns:
    list of tuples: Each tuple contains (heading, content).
    """
    pattern = rf'^{"#" * level} (.+)$'
    sections = re.split(pattern, text, flags=re.MULTILINE)
    
    # The first element is the text before the first heading (if any)
    if sections[0].strip():
        result = [("Introduction", sections[0].strip())]
    else:
        result = []
    
    # Pair up the headings with their content
    for i in range(1, len(sections), 2):
        heading = sections[i].strip()
        content = sections[i+1].strip() if i+1 < len(sections) else ""
        result.append((heading, content))
    
    return result

def split_by_sections(text, min_section_length=500):
    """
    Split the text into sections based on page breaks or large gaps in the text.
    Returns a list of tuples (section_number, content).
    """
    # Split the text by page breaks or multiple newlines
    raw_sections = re.split(r'\n{3,}|\f', text)
    
    sections = []
    current_section = ""
    section_number = 1
    
    for raw_section in raw_sections:
        cleaned_section = raw_section.strip()
        if len(cleaned_section) < min_section_length:
            current_section += "\n\n" + cleaned_section
        else:
            if current_section:
                sections.append((f"Section {section_number}", current_section.strip()))
                section_number += 1
            current_section = cleaned_section
    
    # Add the last section if it's not empty
    if current_section:
        sections.append((f"Section {section_number}", current_section.strip()))
    
    return sections

if __name__ == "__main__":
    # Test the preprocessor
    test_text = """
    # Introduction

    Hello, world! This is a sample text with some special characters: @#$%^&*().
    It preserves punctuation and sentence structure. The weather is great; we should go out.

    ## Section 1

    We'll preprocess this text to see how it works.
    This is part of the same paragraph.

    ## Section 2

    This is a new paragraph.
    It has multiple sentences. Each with its own structure!

    # Conclusion

    That's all for now.
    """
    
    try:
        processed_text = preprocess_text(test_text)
        print("Original text:")
        print(test_text)
        print("\nPreprocessed text:")
        print(processed_text)
        
        print("\nSplit into sentences:")
        sentences = split_into_sentences(processed_text)
        for i, sentence in enumerate(sentences, 1):
            print(f"{i}. {sentence}")
        
        print("\nSplit into paragraphs:")
        paragraphs = split_into_paragraphs(processed_text)
        for i, paragraph in enumerate(paragraphs, 1):
            print(f"Paragraph {i}:")
            print(paragraph)
            print()
        
        print("Split by markdown headings:")
        sections = split_by_markdown_headings(processed_text)
        for heading, content in sections:
            if heading:
                print(f"\n{heading}")
            print(content)
    except Exception as e:
        print(f"An error occurred during testing: {str(e)}")