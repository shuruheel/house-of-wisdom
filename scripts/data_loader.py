import json
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BookNotFoundError(Exception):
    """Custom exception for when a book is not found."""
    pass

def ensure_directory_exists(directory):
    """Ensure that the given directory exists, creating it if necessary."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def load_book_content(book_name):
    """
    Load the content of a book given its name.
    
    :param book_name: The name of the book to load
    :return: The content of the book as a string
    :raises BookNotFoundError: If the book file is not found
    """
    filename = f"books/{book_name}.txt"
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        logger.info(f"Successfully loaded content for book: {book_name}")
        return content
    except FileNotFoundError as e:
        logger.error(f"Book file not found: {book_name}: {str(e)}")
        raise BookNotFoundError(f"Book file not found: {book_name}") from e
    except Exception as e:
        logger.error(f"Error loading book content for: {book_name}: {str(e)}")
        raise

def load_book_metadata(book_name):
    """
    Load the metadata of a book given its name.
    
    :param book_name: The name of the book to load metadata for
    :return: A dictionary containing the book's metadata, or None if not found
    """
    filename = f"metadata/{book_name}.json"
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            metadata = json.load(file)
        logger.info(f"Successfully loaded metadata for book: {book_name}")
        return metadata
    except FileNotFoundError:
        logger.warning(f"Metadata file for book not found: {book_name}. Returning None.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON metadata for book: {book_name}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading book metadata for: {book_name}: {str(e)}")
        return None

def get_all_book_names():
    """
    Get a list of all book names in the books directory.
    
    :return: A list of book names (without the .txt extension)
    """
    try:
        ensure_directory_exists('books')
        book_files = os.listdir('books')
        book_names = [file.split('.')[0] for file in book_files if file.endswith('.txt')]
        logger.info(f"Found {len(book_names)} books")
        return book_names
    except Exception as e:
        logger.error(f"Error getting book names: {str(e)}")
        return []

def create_empty_metadata(book_name):
    """
    Create an empty metadata file for a book if it doesn't exist.
    
    :param book_name: The name of the book to create metadata for
    """
    filename = f"metadata/{book_name}.json"
    try:
        ensure_directory_exists('metadata')
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump({}, file)
            logger.info(f"Created empty metadata file for book: {book_name}")
    except Exception as e:
        logger.error(f"Error creating empty metadata for book: {book_name}: {str(e)}")

if __name__ == "__main__":
    # Test the functions
    test_book_name = "example_book"  # Replace with an actual book name for testing
    
    try:
        content = load_book_content(test_book_name)
        print(f"Content of book '{test_book_name}' (first 100 chars): {content[:100]}")
    except BookNotFoundError:
        print(f"Book '{test_book_name}' not found. Please ensure it exists in the 'books' directory.")
    
    metadata = load_book_metadata(test_book_name)
    print(f"Metadata of book '{test_book_name}': {metadata if metadata else 'Not found'}")
    
    if not metadata:
        create_empty_metadata(test_book_name)
        print(f"Created empty metadata file for book '{test_book_name}'")
    
    all_names = get_all_book_names()
    print(f"All book names: {all_names}")