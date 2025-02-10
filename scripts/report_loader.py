import json
import os
import logging
from pathlib import Path
import PyPDF2

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReportNotFoundError(Exception):
    """Custom exception for when a report is not found."""
    pass

def ensure_directory_exists(directory):
    """Ensure that the given directory exists, creating it if necessary."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def load_report_content(report_name):
    """
    Load the content of a report given its name.
    
    :param report_name: The name of the report to load
    :return: The content of the report as a string
    :raises ReportNotFoundError: If the report file is not found
    """
    filename = f"reports/{report_name}.pdf"
    try:
        with open(filename, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        logger.info(f"Successfully loaded content for report: {report_name}")
        return content
    except FileNotFoundError as e:
        logger.error(f"Report file not found: {report_name}: {str(e)}")
        raise ReportNotFoundError(f"Report file not found: {report_name}") from e
    except Exception as e:
        logger.error(f"Error loading report content for: {report_name}: {str(e)}")
        raise

def load_report_metadata(report_name):
    """
    Load the metadata of a report given its name.
    
    :param report_name: The name of the report to load metadata for
    :return: A dictionary containing the report's metadata, or None if not found
    """
    filename = f"metadata/{report_name}.json"
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            metadata = json.load(file)
        logger.info(f"Successfully loaded metadata for report: {report_name}")
        return metadata
    except FileNotFoundError:
        logger.warning(f"Metadata file for report not found: {report_name}. Returning None.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON metadata for report: {report_name}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading report metadata for: {report_name}: {str(e)}")
        return None

def get_all_report_names():
    """
    Get a list of all report names in the reports directory.
    
    :return: A list of report names (without the .pdf extension)
    """
    try:
        ensure_directory_exists('reports')
        report_files = os.listdir('reports')
        report_names = [file.split('.')[0] for file in report_files if file.endswith('.pdf')]
        logger.info(f"Found {len(report_names)} reports")
        return report_names
    except Exception as e:
        logger.error(f"Error getting report names: {str(e)}")
        return []

def create_empty_metadata(report_name):
    """
    Create an empty metadata file for a report if it doesn't exist.
    
    :param report_name: The name of the report to create metadata for
    """
    filename = f"metadata/{report_name}.json"
    try:
        ensure_directory_exists('metadata')
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump({}, file)
            logger.info(f"Created empty metadata file for report: {report_name}")
    except Exception as e:
        logger.error(f"Error creating empty metadata for report: {report_name}: {str(e)}")

if __name__ == "__main__":
    # Test the functions
    test_report_name = "example_report"  # Replace with an actual report name for testing
    
    try:
        content = load_report_content(test_report_name)
        print(f"Content of report '{test_report_name}' (first 100 chars): {content[:100]}")
    except ReportNotFoundError:
        print(f"Report '{test_report_name}' not found. Please ensure it exists in the 'reports' directory.")
    
    metadata = load_report_metadata(test_report_name)
    print(f"Metadata of report '{test_report_name}': {metadata if metadata else 'Not found'}")
    
    if not metadata:
        create_empty_metadata(test_report_name)
        print(f"Created empty metadata file for report '{test_report_name}'")
    
    all_names = get_all_report_names()
    print(f"All report names: {all_names}")