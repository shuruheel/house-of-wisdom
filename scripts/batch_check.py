import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Load the API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client with the API key
client = OpenAI(api_key=api_key)

# Retrieve the batch and store the response
response = client.batches.retrieve("batch_c2qOTgE6JO5OM4GwKXUaV2LN")
response1 = client.batches.retrieve("batch_YcBCdUmmfb9H2Awn44SWvPFl")
response2 = client.batches.retrieve("batch_vYdXPmkdNqqgLX9h0RxdJK71")

# Alternatively, you can print specific attributes of the response
print(f"Batch ID: {response.id}")
print(f"Status: {response.status}")
print(f"File: {response.output_file_id}\n")

print(f"Batch ID: {response1.id}")
print(f"Status: {response1.status}")
print(f"File: {response1.output_file_id}\n")

print(f"Batch ID: {response2.id}")
print(f"Status: {response2.status}")
print(f"File: {response2.output_file_id}")