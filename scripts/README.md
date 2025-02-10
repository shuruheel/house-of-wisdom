Sorry, this part of the project is messy at the moment. 

With these scripts I:

Processed the full text data chunk by chunk
Transformed each chunk into a JSON object based on the graph schema using an LLM
Populated a Neo4j graph database with nodes and relationships from the transformed JSON files
Added embeddings to key nodes for efficient retrieval


Ideally, the UI should just allow users to upload data, that then goes through a proper version of this data processing pipeline and creates the knowledge graph database automatically in the background. 


