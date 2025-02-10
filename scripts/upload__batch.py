import os
from openai import OpenAI
from dotenv import load_dotenv
import logging
import glob

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def upload_batch_file(client, file_path):
    """Upload the batch file to OpenAI."""
    try:
        with open(file_path, "rb") as file:
            batch_input_file = client.files.create(
                file=file,
                purpose="batch"
            )
        logging.info(f"Batch file uploaded successfully. File ID: {batch_input_file.id}")
        return batch_input_file.id
    except Exception as e:
        logging.error(f"Error uploading batch file: {str(e)}")
        return None

def create_batch(client, file_id):
    """Create a batch using the uploaded file."""
    try:
        batch = client.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "description": "Constitution analysis batch job"
            }
        )
        logging.info(f"Batch created successfully. Batch ID: {batch.id}")
        return batch.id
    except Exception as e:
        logging.error(f"Error creating batch: {str(e)}")
        return None

def main():
    # Initialize OpenAI client
    client = OpenAI()

    # Get all batch files
    batch_files = glob.glob("j_batch_requests_*.jsonl")
    
    if not batch_files:
        logging.error("No batch files found.")
        return

    for batch_file in batch_files:
        logging.info(f"Processing batch file: {batch_file}")
        
        # Upload batch file
        file_id = upload_batch_file(client, batch_file)
        if not file_id:
            logging.error(f"Failed to upload {batch_file}. Skipping to next file.")
            continue

        # Create batch
        batch_id = create_batch(client, file_id)
        if not batch_id:
            logging.error(f"Failed to create batch for {batch_file}. Skipping to next file.")
            continue

        logging.info(f"Batch upload and creation process completed successfully for {batch_file}.")

    logging.info("All batch files processed.")

if __name__ == "__main__":
    main()