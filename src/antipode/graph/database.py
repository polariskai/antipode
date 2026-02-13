"""
Neo4j database connection and operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from neo4j import GraphDatabase as Neo4jDriver, Driver

import logging

logger = logging.getLogger(__name__)


class GraphDatabase:
    """Neo4j graph database wrapper"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None
        self._connected = False

    def _ensure_connected(self):
        """Ensure database connection is established"""
        if not self._connected:
            self._connect()

    def _connect(self):
        """Establish connection to Neo4j"""
        if self._connected:
            return

        try:
            from neo4j import GraphDatabase as Neo4jDriver
            self.driver = Neo4jDriver.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.uri}")
            self._connected = True
            self._create_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.error("Please ensure Neo4j is running and credentials are correct")
            raise
    
    def _create_constraints(self):
        """Create unique constraints and indexes"""
        # Note: Neo4j syntax varies by version. Using try-except for compatibility
        constraints = [
            # Entity constraints - try different syntaxes
            ("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",),
            ("CREATE CONSTRAINT entity_id_unique FOR (e:Entity) REQUIRE e.id IS UNIQUE",),
            # Entity name indexes for search and matching
            ("CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",),
            ("CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",),
            ("CREATE INDEX address_full IF NOT EXISTS FOR (a:Address) ON (a.full_address)",),
            # Compliance-specific indexes
            ("CREATE INDEX filing_date IF NOT EXISTS FOR (f:Filing) ON (f.filing_date)",),
            ("CREATE INDEX event_date IF NOT EXISTS FOR (e:Event) ON (e.event_date)",),
            ("CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.event_type)",),
            ("CREATE INDEX person_nationality IF NOT EXISTS FOR (p:Person) ON (p.nationality)",),
            ("CREATE INDEX company_jurisdiction IF NOT EXISTS FOR (c:Company) ON (c.jurisdiction)",),
        ]

        with self.driver.session() as session:
            for constraint_tuple in constraints:
                constraint = constraint_tuple[0]
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint/index: {constraint[:50]}...")
                except Exception as e:
                    # Try alternative syntax or skip if already exists
                    logger.debug(f"Constraint/index creation: {e}")
                    pass
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        self._ensure_connected()

        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Alias for execute_query - used by compliance modules"""
        return self.execute_query(query, parameters)

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get a single entity by ID"""
        query = """
        MATCH (e:Entity {id: $entity_id})
        RETURN e
        """
        result = self.execute_query(query, {"entity_id": entity_id})
        return result[0] if result else None

    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for an entity"""
        query = """
        MATCH (e:Entity {id: $entity_id})-[r]-(related:Entity)
        RETURN type(r) as type, related, properties(r) as props
        """
        return self.execute_query(query, {"entity_id": entity_id})

    def update_entity_metadata(self, entity_id: str, metadata: Dict[str, Any]) -> bool:
        """Update entity metadata"""
        query = """
        MATCH (e:Entity {id: $entity_id})
        SET e.metadata = $metadata
        RETURN e
        """
        result = self.execute_query(query, {"entity_id": entity_id, "metadata": metadata})
        return len(result) > 0

    def create_entity(self, entity_data: Dict[str, Any], entity_type: str) -> str:
        """Create or update an entity node"""
        entity_id = entity_data.get("id")
        if not entity_id:
            raise ValueError("Entity must have an 'id' field")
        
        # Filter out nested dicts and convert to JSON strings for metadata
        # Neo4j doesn't support nested maps directly
        clean_data = {}
        for k, v in entity_data.items():
            if k == "id":
                continue
            if isinstance(v, dict):
                # Convert nested dicts to JSON string
                import json
                clean_data[k] = json.dumps(v)
            elif isinstance(v, (datetime, date)):
                # Convert datetime to ISO string
                clean_data[k] = v.isoformat()
            else:
                clean_data[k] = v
        
        clean_data['entity_type'] = entity_type
        
        # Use parameterized label (entity_type)
        query = f"""
        MERGE (e:Entity {{id: $id}})
        SET e += $props
        SET e:{entity_type}
        RETURN e.id as id
        """
        
        params = {"id": entity_id, "props": clean_data}
        result = self.execute_query(query, params)
        return result[0]["id"] if result else entity_id
    
    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a relationship between two entities"""
        query = f"""
        MATCH (a:Entity {{id: $from_id}})
        MATCH (b:Entity {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties
        RETURN r
        """
        
        params = {
            "from_id": from_id,
            "to_id": to_id,
            "properties": properties or {}
        }
        
        result = self.execute_query(query, params)
        return len(result) > 0
    
    def get_entity_context(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get full context of an entity including relationships"""
        query = f"""
        MATCH path = (e:Entity {{id: $entity_id}})-[*1..{depth}]-(related:Entity)
        WITH e, collect(DISTINCT related) as related_entities,
             collect(DISTINCT path) as paths

        // Extract ALL relationships from all paths (not just depth 1)
        UNWIND paths as p
        UNWIND relationships(p) as r

        RETURN e,
               collect(DISTINCT {{from: startNode(r).id, to: endNode(r).id,
                                 type: type(r), props: properties(r)}}) as relationships,
               related_entities
        """

        result = self.execute_query(query, {"entity_id": entity_id})
        if result:
            return result[0]
        return {}
    
    def find_entities_by_name(self, name: str, entity_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Find entities by name (fuzzy search with improved partial matching)"""
        type_filter = f":{entity_type}" if entity_type else ""

        # Split search term into words for better partial matching
        # This allows "Tim Cook" to match "Timothy D. Cook, CEO"
        search_words = [word.strip() for word in name.lower().split() if word.strip()]

        if not search_words:
            return []

        # Build WHERE clause that checks if ALL search words appear in the entity name
        # This handles cases like:
        # - "Tim Cook" matches "Timothy D. CookChief Executive Officer"
        # - "Apple" matches "Apple Inc."
        where_conditions = []
        params = {"limit": limit}

        for i, word in enumerate(search_words):
            param_name = f"word{i}"
            where_conditions.append(f"toLower(e.name) CONTAINS ${param_name}")
            params[param_name] = word

        where_clause = " AND ".join(where_conditions)

        query = f"""
        MATCH (e:Entity{type_filter})
        WHERE {where_clause}
        RETURN e
        LIMIT $limit
        """

        return self.execute_query(query, params)
    
    def get_ownership_chain(self, company_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Get ownership chain for a company"""
        query = f"""
        MATCH path = (c:Company {{id: $company_id}})<-[:OWNS*1..{max_depth}]-(owner)
        WITH path, relationships(path) as rels
        RETURN path, rels
        ORDER BY length(path)
        """
        
        return self.execute_query(query, {"company_id": company_id})
    
    def find_shared_addresses(self, entity_id: str) -> List[Dict[str, Any]]:
        """Find entities sharing the same address"""
        query = """
        MATCH (e:Entity {id: $entity_id})-[:REGISTERED_AT]->(a:Address)
        MATCH (other:Entity)-[:REGISTERED_AT]->(a)
        WHERE other.id <> $entity_id
        RETURN other, a
        """
        
        return self.execute_query(query, {"entity_id": entity_id})



