Neo4j Graph Database Schema

# Node type definitions
NODE_TYPES = [
    "Amendment", "Article", "Attribute", "BillOfRights", "Book", "Chapter",
    "Claim", "Concept", "Condition", "Consequence", "Constitution", "DataPoint",
    "Definition", "Emotion", "Entity", "Event", "Law", "LegalCode", "Location",
    "Poetry", "Proposition", "Provision", "ReasoningChain", "ReasoningStep",
    "Report", "ScientificInsight", "Scope", "Thought", "Title"
]

# Amendment Node Template
```json
{
  "content": "Amendment content text",
  "title": "Amendment title",
  "number": "Amendment number",
  "embedding": [0.1, 0.2, ...]
}
```

# Article Node Template
```json
{
  "content": "Article content text",
  "title": "Article title",
  "number": "Article number",
  "embedding": [0.1, 0.2, ...]
}
```

# Attribute Node Template
```json
{
  "name": "Attribute Name",
  "nodeType": "Attribute",
  "description": "Description of what this attribute represents",
  "possibleValues": ["value1", "value2"],
  "mentions": ["mention1", "mention2"],
  "unit": "unit of measurement if applicable",
  "value": "attribute value",
  "valueType": "numeric/categorical/boolean/text"
}
```

# BillOfRights Node Template
```json
{
  "name": "Bill of Rights name"
}
```

# Book Node Template
```json
{
  "name": "Book name"
}
```

# Chapter Node Template
```json
{
  "chapter_title": "Chapter title",
  "number": "Chapter number",
  "chapter_number": "Chapter number",
  "book": "Book name",
  "migrationHash": "hash value",
  "label": "Chapter label",
  "title_number": "Title number"
}
```

# Claim Node Template
```json
{
  "source": "Source of the claim",
  "confidence": 0.8,
  "contentHash": "hash value",
  "timestamp": "ISO datetime",
  "content": "Claim content text",
  "embedding": [0.1, 0.2, ...]
}
```

# Concept Node Template
```json
{
  "name": "Concept Name",
  "nodeType": "Concept",
  "description": "Expanded explanation",
  "definition": "Concise definition (1-2 sentences)",
  "domain": "Field this belongs to",
  "significance": "Importance or impact",
  "language": "Language code",
  "chapter_number": "Chapter number",
  "book_name": "Book name",
  "embedding": [0.1, 0.2, ...]
}
```

# Condition Node Template
```json
{
  "title_number": "Title number",
  "content": "Condition content text",
  "chapter_number": "Chapter number",
  "section_title": "Section title",
  "section_number": "Section number",
  "migrationHash": "hash value",
  "label": "Condition label",
  "contentHash": "hash value"
}
```

# Consequence Node Template
```json
{
  "title_number": "Title number",
  "content": "Consequence content text",
  "chapter_number": "Chapter number",
  "section_title": "Section title",
  "section_number": "Section number",
  "migrationHash": "hash value",
  "label": "Consequence label",
  "contentHash": "hash value"
}
```

# Constitution Node Template (LegalCode subtype)
```json
{
  "name": "Constitution name",
  "government_level": "Federal/State/Local",
  "jurisdiction": "Jurisdiction name",
  "type": "Constitution type"
}
```

# DataPoint Node Template
```json
{
  "name": "DataPoint name",
  "description": "Description of the data point",
  "unit": "Unit of measurement",
  "value": "Data point value"
}
```

# Definition Node Template
```json
{
  "title_number": "Title number",
  "content": "Definition content text",
  "chapter_number": "Chapter number",
  "section_title": "Section title",
  "section_number": "Section number",
  "migrationHash": "hash value",
  "label": "Definition label",
  "contentHash": "hash value"
}
```

# Entity Node Template
```json
{
  "name": "Entity Name",
  "nodeType": "Entity",
  "subType": "Person/Organization/Location/Artifact/Animal/Concept",
  "description": "General description",
  "biography": "Biographical information",
  "keyContributions": ["Contribution 1", "Contribution 2"],
  "observations": ["Factual observation 1", "Factual observation 2"],
  "emotionalValence": 0.5,
  "emotionalArousal": 1.0,
  "personalityTraits": ["trait1", "trait2"],
  "personalitySummary": "Summary of personality",
  "cognitiveStyle": "Cognitive style description",
  "decisionMaking": "Decision making approach",
  "emotionalProfile": "Emotional profile description",
  "emotionalDisposition": "Emotional disposition",
  "relationalDynamics": "Relational dynamics description",
  "interpersonalStyle": "Interpersonal style",
  "valueSystem": "Value system description",
  "ethicalFramework": "Ethical framework",
  "psychologicalDevelopment": "Psychological development description",
  "source": "Source of information",
  "confidence": 0.9,
  "language": "Language code",
  "type": "Entity type",
  "embedding": [0.1, 0.2, ...]
}
```


# Emotion Node Template
```json
{
  "name": "Emotion Name",
  "nodeType": "Emotion",
  "description": "Description of the emotional experience",
  "intensity": 0.7,
  "subcategory": "More specific emotion category",
  "category": "Joy/Sadness/Anger/etc.",
  "mentions": ["mention1", "mention2"],
  "valence": 0.5
}
```

# Event Node Template
```json
{
  "name": "Event Name",
  "nodeType": "Event",
  "description": "Event description",
  "significance": "Why this matters",
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "emotion": "Emotion name",
  "date_precision": "Precision level",
  "end_date": "End date",
  "status": "Ongoing/Concluded/Planned",
  "start_date": "Start date",
  "embedding": [0.1, 0.2, ...],
  "emotion_intensity": 0.7,
  "next_event": "Next event name",
  "location": "Where it occurred",
  "outcome": "Result of the event"
}
```




# Proposition Node Template
```json
{
  "name": "Short Label",
  "nodeType": "Proposition",
  "emotionalValence": 0.5,
  "emotionalArousal": 1.0,
  "confidence": 0.8,
  "domain": "Knowledge domain",
  "statement": "The objectively verifiable assertion",
  "truthValue": true,
  "status": "fact/hypothesis/law/rule/claim",
  "sources": ["Source1", "Source2"],
  "counterEvidence": ["Counter evidence 1", "Counter evidence 2"],
  "evidenceStrength": 0.8
}
```

# LegalCode Node Template
```json
{
  "name": "Legal Code name",
  "doc_number": "Document number",
  "government_level": "Federal/State/Local",
  "jurisdiction": "Jurisdiction name"
}
```

# Law Node Template
```json
{
  "name": "Law Name",
  "nodeType": "Law",
  "emotionalValence": 0.5,
  "emotionalArousal": 1.0,
  "domain": "Field where law applies",
  "statement": "The law's statement",
  "counterexamples": ["Counterexample 1", "Counterexample 2"],
  "formalRepresentation": "Mathematical or logical formulation",
  "conditions": ["condition1", "condition2"],
  "domainConstraints": ["Constraint 1", "Constraint 2"],
  "proofs": ["Proof 1", "Proof 2"],
  "historicalPrecedents": ["Precedent 1", "Precedent 2"],
  "mentions": ["mention1", "mention2"],
  "exceptions": ["exception1", "exception2"]
}
```

# Location Node Template
```json
{
  "name": "Location Name",
  "nodeType": "Location",
  "description": "Description of location",
  "locationType": "City/Country/Building/Virtual/etc.",
  "locationSignificance": "Historical, cultural, or personal importance",
  "latitude": 0.0,
  "longitude": 0.0
}
```

# Poetry Node Template
```json
{
  "source": "Source of the poetry",
  "content": "Poetry content text",
  "language": "Language code",
  "poet": "Poet name",
  "translation": "Translation text",
  "contentHash": "hash value"
}
```

# Provision Node Template
```json
{
  "embedding": [0.1, 0.2, ...],
  "contentHash": "hash value",
  "content": "Provision content text",
  "chapter_number": "Chapter number",
  "section_title": "Section title",
  "section_number": "Section number",
  "label": "Provision label",
  "title_number": "Title number"
}
```

# Reasoning Chain Node Template
```json
{
  "name": "Reasoning Chain Name",
  "nodeType": "ReasoningChain",
  "description": "What this reasoning accomplishes",
  "domain": "Field or domain of the reasoning",
  "tags": ["Tag1", "Tag2"],
  "steps": ["Step1", "Step2"],
  "mentions": ["mention1", "mention2"],
  "relatedPropositions": ["Proposition 1", "Proposition 2"],
  "confidenceScore": 0.8,
  "methodology": "deductive/inductive/abductive/analogical/mixed",
  "numberOfSteps": 3,
  "sourceThought": "Thought that initiated this reasoning",
  "stepDetails": ["Detail1", "Detail2"],
  "creator": "Who created this reasoning",
  "conclusion": "Final conclusion reached",
  "alternativeConclusionsConsidered": ["Alternative 1", "Alternative 2"]
}
```

# Reasoning Step Node Template
```json
{
  "name": "Step Name",
  "nodeType": "ReasoningStep",
  "confidence": 0.8,
  "content": "The actual reasoning content",
  "counterarguments": ["Counterargument 1", "Counterargument 2"],
  "evidenceType": "observation/fact/assumption/inference/expert_opinion/statistical_data",
  "mentions": ["mention1", "mention2"],
  "alternatives": ["Alternative 1", "Alternative 2"],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "supportingReferences": ["Reference 1", "Reference 2"],
  "formalNotation": "Logical or mathematical notation",
  "propositions": ["Proposition 1", "Proposition 2"],
  "chainName": "Parent reasoning chain name",
  "order": 1,
  "stepType": "premise/inference/evidence/counterargument/rebuttal/conclusion"
}
```

# Report Node Template
```json
{
  "name": "Report name",
  "title": "Report title",
  "organization": "Organization name"
}
```

# Scientific Insight Node Template
```json
{
  "name": "Insight Name",
  "nodeType": "ScientificInsight",
  "emotionalValence": 0.5,
  "emotionalArousal": 1.0,
  "confidence": 0.85,
  "mentions": ["mention1", "mention2"],
  "evidenceStrength": 0.8,
  "applicationDomains": ["Domain 1", "Domain 2"],
  "hypothesis": "The scientific hypothesis",
  "evidence": ["Evidence1", "Evidence2"],
  "methodology": "Research approach",
  "field": "Scientific discipline",
  "surpriseValue": 0.6,
  "publications": ["Publication 1", "Publication 2"],
  "replicationStatus": "Current replication consensus",
  "scientificCounterarguments": ["Counterargument 1", "Counterargument 2"]
}
```

# Scope Node Template
```json
{
  "embedding": [0.1, 0.2, ...],
  "contentHash": "hash value",
  "content": "Scope content text",
  "chapter_number": "Chapter number",
  "section_title": "Section title",
  "section_number": "Section number",
  "label": "Scope label",
  "title_number": "Title number"
}
```

# Thought Node Template
```json
{
  "name": "Thought Label",
  "nodeType": "Thought",
  "emotionalValence": 0.5,
  "emotionalArousal": 1.0,
  "source": "Who originated this thought",
  "confidence": 0.7,
  "evidentialBasis": ["Evidence 1", "Evidence 2"],
  "tags": ["Tag1", "Tag2"],
  "thoughtCounterarguments": ["Counterargument 1", "Counterargument 2"],
  "references": ["Entity1", "Concept1"],
  "createdBy": "Author of the thought",
  "thoughtContent": "The subjective analysis or interpretation",
  "implications": ["Implication 1", "Implication 2"],
  "reasoningChains": ["Reasoning chain 1", "Reasoning chain 2"],
  "impact": "Potential impact or importance",
  "thoughtConfidenceScore": 0.8
}
```

# Title Node Template
```json
{
  "name": "Title name",
  "title": "Title text",
  "government_level": "Federal/State/Local",
  "jurisdiction": "Jurisdiction name",
  "type": "Title type",
  "effective_date": "YYYY-MM-DD",
  "title_number": "Title number"
}
```

# Define relationship categories
RELATIONSHIP_CATEGORIES = [
    "hierarchical",  # parent-child, category-instance
    "lateral",       # similarity, contrast, analogy
    "temporal",      # before-after, causes-results
    "compositional", # part-whole, component-system
    "causal",        # causes-effect relationships
    "attributive"    # entity-property relationships
]

# Define relationship types
RELATIONSHIP_TYPES = [
    # Hierarchical relationships
    "IS_A", "INSTANCE_OF", "SUB_CLASS_OF", "SUPER_CLASS_OF",
    
    # Compositional relationships
    "HAS_PART", "PART_OF", "PART_OF_CHAIN",
    
    # Spatial relationships
    "LOCATED_IN", "HAS_LOCATION", "CONTAINED_IN", "CONTAINS", "OCCURRED_AT", "VISITED", "ATTENDED",
    
    # Temporal relationships
    "HAS_TIME", "OCCURS_ON", "BEFORE", "AFTER", "DURING",
    
    # Participation relationships
    "PARTICIPANT", "HAS_PARTICIPANT", "AGENT", "HAS_AGENT", "PATIENT", "HAS_PATIENT", "INVOLVED_IN", 
    "PARTICIPATED_IN", "JOINS",
    
    # Causal relationships
    "CAUSES", "CAUSED_BY", "INFLUENCES", "INFLUENCED_BY", "CAUSED",
    
    # Sequential relationships
    "NEXT", "PREVIOUS",
    
    # Social relationships
    "KNOWS", "FRIEND_OF", "MEMBER_OF", "APPOINTED", "FOUNDED", "FOUNDER_OF", "CHAIRMAN_OF",
    
    # Property relationships
    "HAS_PROPERTY", "PROPERTY_OF",
    
    # General relationships
    "RELATED_TO", "ASSOCIATED_WITH", "REFERENCES",
    
    # Emotional relationships
    "EXPRESSES_EMOTION", "FEELS", "EVOKES_EMOTION",
    
    # Belief relationships
    "BELIEVES", "SUPPORTS", "CONTRADICTS", "PROPOSED", "ACCEPTS", "SUPPORTED_BY", "ADVOCATED_FOR",
    "OPPOSITION_TO", 
    
    # Competition relationships
    "COMPETES_WITH",
    
    # Source relationships
    "DERIVED_FROM", "CITES", "SOURCE",
    
    # Economic relationships
    "NATIONALIZATION_OF",
    
    # Symbolic relationships
    "ICON_OF",
    
    # Person-specific relationships
    "MENTORS", "MENTORED_BY", "ADMIRES", "ADMIRED_BY", "OPPOSES", "OPPOSED_BY",
    "SHAPED_BY", "TRANSFORMED", "EXHIBITS_TRAIT", "HAS_PERSONALITY", 
    "HAS_COGNITIVE_STYLE", "STRUGGLES_WITH", "VALUES", "ADHERES_TO", 
    "REJECTS", "HAS_ETHICAL_FRAMEWORK", "LOYAL_TO"
]