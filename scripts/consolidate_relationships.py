import os
import time
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jRelationshipConsolidator:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def consolidate_relationships(self):
        with self.driver.session() as session:
                        
            # Causal Relationships
            self._consolidate_causation(session)

            # Support and Opposition
            self._consolidate_support_opposition(session)

            # Influence and Impact
            self._consolidate_influence_impact(session)

            # Political and Diplomatic Relationships
            self._consolidate_political_diplomatic(session)

            # Other Consolidations
            self._consolidate_member_component(session)
            self._consolidate_collaboration(session)
            self._consolidate_requirement_enhancement(session)
            self._consolidate_leadership(session)
            self._consolidate_definition(session)
            self._consolidate_is_a(session)

    def _get_relationship_count(self, session, rel_type):
        query = f"""
        MATCH ()-[r:{rel_type}]->()
        RETURN count(r) as count
        """
        result = session.run(query)
        return result.single()["count"]

    def _handle_reciprocal_relationships(self, session, rel_type):
        query = f"""
        MATCH (a)-[r1:{rel_type}]->(b)
        MATCH (b)-[r2:{rel_type}]->(a)
        WHERE id(r1) < id(r2)
        SET r1.reciprocal = true, r2.reciprocal = true
        RETURN count(r1) as count
        """
        result = session.run(query)
        count = result.single()["count"]
        logger.info(f"Marked {count} pairs of reciprocal {rel_type} relationships")

    def _process_relationship_batch(self, session, rel, inverse_rel):
        total_count = self._get_relationship_count(session, inverse_rel)
        logger.info(f"Found {total_count} {inverse_rel} relationships to consolidate")

        query = f"""
        MATCH (start)-[r:{inverse_rel}]->(end)
        WHERE NOT EXISTS((end)-[:{rel}]->(start)) AND r.reciprocal IS NULL
        WITH start, r, end
        LIMIT 10
        MERGE (end)-[new_rel:{rel}]->(start)
        ON CREATE SET new_rel = properties(r)
        DELETE r
        RETURN count(r) as count
        """
        processed_count = 0
        while True:
            result = session.run(query)
            count = result.single()["count"]
            if count == 0:
                break
            processed_count += count
            logger.info(f"Consolidated {processed_count}/{total_count} {inverse_rel} relationships to {rel}")
            time.sleep(0.01)  # Small delay to prevent overwhelming the database
        logger.info(f"Finished consolidating {processed_count} {inverse_rel} relationships to {rel}")

    def _consolidate_with_type(self, session, new_rel, old_rels, type_property):
        for old_rel in old_rels:
            self._handle_reciprocal_relationships(session, old_rel)

        old_rels_str = '|'.join(old_rels)
        total_count = sum(self._get_relationship_count(session, rel) for rel in old_rels)
        logger.info(f"Found {total_count} relationships to consolidate into {new_rel}")

        query = f"""
        MATCH (start)-[r:{old_rels_str}]->(end)
        WHERE NOT EXISTS((start)-[:{new_rel}]->(end)) AND r.reciprocal IS NULL
        WITH start, r, end
        LIMIT 10
        MERGE (start)-[new_rel:{new_rel}]->(end)
        ON CREATE SET new_rel = properties(r),
            new_rel.{type_property} = type(r)
        DELETE r
        RETURN count(r) as count
        """
        processed_count = 0
        while True:
            result = session.run(query)
            count = result.single()["count"]
            if count == 0:
                break
            processed_count += count
            logger.info(f"Consolidated {processed_count}/{total_count} relationships to {new_rel}")
            time.sleep(0.01)  # Small delay to prevent overwhelming the database
        logger.info(f"Finished consolidating {processed_count} relationships to {new_rel}")

    def _consolidate_causation(self, session):
        self._consolidate_with_type(
            session,
            "CAUSES",
            ["LEADS_TO", "RESULTS_IN", "CONTRIBUTES_TO", "ENABLES", "FACILITATES", "DRIVES", "TRIGGERS", "INDUCES", "PROMOTES"],
            "causation_type"
        )

    def _consolidate_support_opposition(self, session):
        self._consolidate_with_type(
            session,
            "SUPPORTS",
            ["SUPPORTS", "SUPPORT", "SUPPORTIVE", "SUPPORTED_BY", "SUPPORTED"],
            "support_type"
        )

        self._consolidate_with_type(
            session,
            "OPPOSES",
            ["OPPOSES", "OPPOSITION", "CONTRADICTS", "CONTRAST", "CONTRADICTION", "CONTRADICTORY"],
            "opposition_type"
        )

    def _consolidate_influence_impact(self, session):
        self._consolidate_with_type(
            session,
            "INFLUENCES",
            ["INFLUENCES", "INFLUENCED_BY", "INFLUENCED", "INFLUENTIAL", "INFLUENCE", "IMPACT", "IMPACTS", "INFLUENCING"],
            "influence_type"
        )

    def _consolidate_political_diplomatic(self, session):
        self._consolidate_with_type(
            session,
            "ALLIED_WITH",
            ["ALLY", "ALLIANCE"],
            "alliance_type"
        )

        self._consolidate_with_type(
            session,
            "DIPLOMATIC_RELATION",
            ["DIPLOMATIC", "DIPLOMATIC_PARTNER", "DIPLOMATIC_RELATION", "DIPLOMATIC_COUNTERPART", "DIPLOMATIC_TENSION"],
            "diplomatic_type"
        )

        self._consolidate_with_type(
            session,
            "FOREIGN_RELATION",
            ["FOREIGN_RELATIONS", "INTERNATIONAL_COOPERATION", "INTERNATIONAL_RELATION", "TREATY_PARTNER"],
            "relation_type"
        )

        self._consolidate_with_type(
            session,
            "MILITARY_COOPERATION",
            ["MILITARY_COOPERATION"],
            "cooperation_type"
        )

        self._consolidate_with_type(
            session,
            "NUCLEAR_COOPERATION",
            ["NUCLEAR_COOPERATION"],
            "cooperation_type"
        )

        self._consolidate_with_type(
            session,
            "TRADE_PARTNER",
            ["TRADE_PARTNER"],
            "trade_type"
        )

    def _consolidate_member_component(self, session):
        self._consolidate_with_type(
            session,
            "MEMBER_OF",
            ["MEMBER", "MEMBER_OF", "MEMBER_STATE"],
            "member_type"
        )

        self._consolidate_with_type(
            session,
            "PART_OF",
            ["COMPONENT", "COMPONENT_OF"],
            "part_of_type"
        )

    def _consolidate_collaboration(self, session):
        self._consolidate_with_type(
            session,
            "COLLABORATES_WITH",
            ["COLLABORATES_WITH", "COLLABORATOR", "COLLABORATES", "COLLABORATION", "COLLABORATED_WITH"],
            "collaboration_type"
        )

    def _consolidate_requirement_enhancement(self, session):
        self._consolidate_with_type(
            session,
            "REQUIRES",
            ["REQUIRES", "REQUIREMENT"],
            "requirement_type"
        )

        self._consolidate_with_type(
            session,
            "ENHANCES",
            ["ENHANCES", "ENHANCEMENT"],
            "enhancement_type"
        )

    def _consolidate_leadership(self, session):
        self._consolidate_with_type(
            session,
            "LEADS",
            ["LEADER", "LEADER_OF", "LEADERSHIP", "LED_BY"],
            "leadership_type"
        )

    def _consolidate_definition(self, session):
        self._consolidate_with_type(
            session,
            "DEFINES",
            ["DEFINES", "DEFINITIONAL"],
            "definition_type"
        )

    def _consolidate_is_a(self, session):
        self._consolidate_with_type(
            session,
            "IS_A",
            ["IS_A_TYPE_OF", "IS_A_FORM_OF", "IS_AN_EXAMPLE_OF", "INSTANCE_OF", "SUBSET_OF"],
            "classification_type"
        )

    def create_indexes(self):
        with self.driver.session() as session:
            indexes = [
                ("CAUSES", "causation_type"),
                ("CONTRADICTS", "contradiction_type"),
                ("RELATED_TO", "relation_type"),
                ("DEPENDS_ON", "dependency_type"),
                ("IS_A", "classification_type"),
                ("INFLUENCES", "influence_type"),
                ("SUPPORTS", "support_type"),
                ("INVOLVES", "involvement_type"),
                ("PART_OF", "part_of_type"),
                ("RELATED", "relation_type"),
                ("ALLIED_WITH", "alliance_type"),
                ("DIPLOMATIC_RELATION", "diplomatic_type"),
                ("FOREIGN_RELATION", "relation_type"),
                ("MILITARY_COOPERATION", "cooperation_type"),
                ("NUCLEAR_COOPERATION", "cooperation_type"),
                ("TRADE_PARTNER", "trade_type"),
                ("MEMBER_OF", "member_type"),
                ("COLLABORATES_WITH", "collaboration_type"),
                ("REQUIRES", "requirement_type"),
                ("ENHANCES", "enhancement_type"),
                ("LEADS", "leadership_type"),
                ("DEFINES", "definition_type"),
            ]
            for rel, prop in indexes:
                query = f"""
                CREATE INDEX IF NOT EXISTS FOR ()-[r:{rel}]-() ON (r.{prop})
                """
                try:
                    session.run(query)
                    logger.info(f"Created index on :{rel}({prop})")
                except Exception as e:
                    if "EquivalentSchemaRuleAlreadyExists" in str(e):
                        logger.info(f"Index on :{rel}({prop}) already exists, skipping.")
                    else:
                        logger.error(f"Error creating index on :{rel}({prop}): {str(e)}")

    def cleanup_duplicate_relationships(self):
        with self.driver.session() as session:
            logger.info("Starting cleanup of duplicate relationships")
            
            # Get all relationship types
            query = "CALL db.relationshipTypes()"
            result = session.run(query)
            rel_types = [record["relationshipType"] for record in result]

            for rel_type in rel_types:
                self._cleanup_duplicates_for_type(session, rel_type)

    def _cleanup_duplicates_for_type(self, session, rel_type):
        query = f"""
        MATCH (a)-[r:{rel_type}]->(b)
        WITH a, b, type(r) AS rel_type, collect(r) AS rels
        WHERE size(rels) > 1
        WITH a, b, rel_type, rels[0] AS kept, rels[1..] AS duplicates
        FOREACH (r IN duplicates | DELETE r)
        RETURN count(duplicates) AS removed_count
        """
        result = session.run(query)
        removed_count = result.single()["removed_count"]
        logger.info(f"Removed {removed_count} duplicate {rel_type} relationships")

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get Neo4j connection details from environment variables
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is not set")

    consolidator = Neo4jRelationshipConsolidator(uri, user, password)
    
    try:
        consolidator.consolidate_relationships()
        consolidator.create_indexes()
        consolidator.cleanup_duplicate_relationships()  # Add this line
    finally:
        consolidator.close()

logger.info("Relationship consolidation and cleanup completed.")