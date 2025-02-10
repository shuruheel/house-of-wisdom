import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Load the API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client with the API key
client = OpenAI(api_key=api_key)

file_response = client.files.content("file-bGesvehNac04Utk1NHqa9ECB")
with open("batch_output1.jsonl", "w") as output_file:
    output_file.write(file_response.text)

file_response = client.files.content("file-O5Vr29pqYOcgZ8hAbhKXsPsB")
with open("batch_output2.jsonl", "w") as output_file:
    output_file.write(file_response.text)

file_response = client.files.content("file-TEtawUWBuyOfiKPXZr0csEes")
with open("batch_output3.jsonl", "w") as output_file:
    output_file.write(file_response.text)