from neo4j import GraphDatabase
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_nodes_batch(self, label: str, batch_size: int, offset: int) -> List[Dict]:
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (n:{label}) "
                "RETURN n.name AS name, n.embedding AS embedding, id(n) AS node_id "
                f"SKIP {offset} LIMIT {batch_size}"
            )
            return [{"name": record["name"], "embedding": record["embedding"], "node_id": record["node_id"]} 
                    for record in result]

    def create_references_batch(self, references: List[Dict]):
        with self.driver.session() as session:
            session.run(
                "UNWIND $refs AS ref "
                "MATCH (source) WHERE id(source) = ref.source_id "
                "MATCH (target) WHERE id(target) = ref.target_id "
                "MERGE (source)-[:REFERENCES]->(target)",
                refs=references
            )

def process_batches(connector: Neo4jConnector, source_label: str, target_label: str, 
                    batch_size: int, similarity_threshold: float):
    offset = 0
    while True:
        source_nodes = connector.get_nodes_batch(source_label, batch_size, offset)
        if not source_nodes:
            break

        target_nodes = connector.get_nodes_batch(target_label, batch_size * 10, 0)  # Assuming targets fit in memory
        
        source_embeddings = np.array([node['embedding'] for node in source_nodes])
        target_embeddings = np.array([node['embedding'] for node in target_nodes])
        
        similarities = cosine_similarity(source_embeddings, target_embeddings)
        
        references = []
        for i, sim_row in enumerate(similarities):
            matches = np.where(sim_row > similarity_threshold)[0]
            for match in matches:
                references.append({
                    "source_id": source_nodes[i]["node_id"],
                    "target_id": target_nodes[match]["node_id"]
                })
        
        connector.create_references_batch(references)
        offset += batch_size

def main():
    connector = Neo4jConnector("neo4j+s://341b38a0.databases.neo4j.io", "neo4j", "vzjcDdEO-0PMJp2BV_dpb4K7C1nGcD6W1C8w4URGxy8")
    
    try:
        # Process Entities referencing Scopes and Definitions
        process_batches(connector, "Entity", "Scope", 1000, 0.7)
        process_batches(connector, "Entity", "Definition", 1000, 0.7)
        
        # Process Concepts referencing Scopes and Definitions
        process_batches(connector, "Concept", "Scope", 1000, 0.7)
        process_batches(connector, "Concept", "Definition", 1000, 0.7)
    finally:
        connector.close()

if __name__ == "__main__":
    main()