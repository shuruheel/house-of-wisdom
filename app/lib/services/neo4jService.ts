import neo4j, { Driver } from 'neo4j-driver';
import { config } from '../config';
import { handleError, AppError } from '../utils/errorHandler';

let driver: Driver | null;

export async function getDriver(): Promise<Driver> {
  if (!driver) {
    try {
      if (!config.neo4j.uri || !config.neo4j.user || !config.neo4j.password) {
        throw new Error('Neo4j configuration is incomplete');
      }
      driver = neo4j.driver(
        config.neo4j.uri,
        neo4j.auth.basic(config.neo4j.user, config.neo4j.password)
      );
      const serverInfo = await driver.getServerInfo();
      console.log('Connection established');
      console.log(serverInfo);
    } catch (err) {
      const error = err as Error;
      console.log(`Connection error\n${error}\nCause: ${error.cause}`);
      throw handleError(error, 'getDriver');
    }
  }
  return driver;
}

export async function closeDriver(): Promise<void> {
  if (driver) {
    await driver.close();
    driver = null;
  }
}

export async function getRelevantEventsAndClaims(
  queryEmbedding: number[],
  maxEvents = 20,
  maxClaims = 20,
  similarityThreshold = 0.3,
  queryDateRange: string | null = null
): Promise<{ events: any[], claims: any[] }> {
  const driver = await getDriver();

  try {
    const { records, summary } = await driver.executeQuery(
      `
        CALL () {
        WITH $query_date_range AS query_date_range
        MATCH (n:Event)
        WHERE n.embedding IS NOT NULL 
        AND n.start_date <= date()
        AND CASE
            WHEN query_date_range = 'recent' THEN n.start_date >= date() - duration('P1Y')
            WHEN query_date_range = 'latest' THEN n.start_date >= date() - duration('P3M')
            WHEN query_date_range = 'historic' THEN n.start_date < date() - duration('P50Y')
            ELSE true
        END
        RETURN n, 'Event' AS type, n.start_date AS start_date, n.emotion AS emotion, n.emotion_intensity AS emotion_intensity, null AS confidence
        UNION
        WITH $query_date_range AS query_date_range
        MATCH (n:Claim)
        WHERE n.embedding IS NOT NULL
        RETURN n, 'Claim' AS type, null AS start_date, null AS emotion, null AS emotion_intensity, n.confidence AS confidence
    }
    WITH n, type, start_date, n.embedding AS embedding, date() AS current_date, emotion, emotion_intensity, confidence

    // Cosine similarity calculation
    WITH n, type, start_date, embedding, current_date, emotion, emotion_intensity, confidence,
        reduce(dot = 0.0, i IN range(0, size(embedding)-1) | dot + embedding[i] * $query_embedding[i]) /
        (sqrt(reduce(l2 = 0.0, i IN range(0, size(embedding)-1) | l2 + embedding[i]^2)) * 
        sqrt(reduce(l2 = 0.0, i IN range(0, size($query_embedding)-1) | l2 + $query_embedding[i]^2))) AS similarity
    WHERE similarity >= $similarity_threshold

    // Time relevance calculation
    WITH n, type, start_date, similarity, current_date, emotion, emotion_intensity, confidence,
        CASE
        WHEN type = 'Event' THEN toFloat(duration.inDays(start_date, current_date).days) / 365.25
        ELSE null
        END AS years_ago

    // Apply time relevance function
    WITH n, type, start_date, similarity, years_ago, current_date, emotion, emotion_intensity, confidence,
        CASE
        WHEN type = 'Event' AND years_ago IS NOT NULL THEN
            CASE
            WHEN $query_date_range = 'recent' THEN
                exp(-years_ago * $recent_coeff)
            WHEN $query_date_range = 'latest' THEN
                exp(-years_ago * $recent_coeff * 2)
            WHEN $query_date_range = 'historic' THEN
                1 - exp(-years_ago / $historic_coeff)
            ELSE 
                1 / (1 + years_ago / $default_coeff)
            END
        WHEN type = 'Claim' THEN 1
        ELSE 0.5
        END AS time_relevance

    // Combine scores
    WITH n, similarity, time_relevance, type, start_date, years_ago, current_date, emotion, emotion_intensity, confidence,
        CASE 
        WHEN type = 'Event' THEN (similarity * 0.7) + (time_relevance * 0.3)
        ELSE similarity
        END AS combined_score

    // Sort and collect results
    ORDER BY combined_score DESC
    WITH type, COLLECT({node: n, score: combined_score, similarity: similarity, time_relevance: time_relevance, start_date: start_date, years_ago: years_ago, current_date: current_date, emotion: emotion, emotion_intensity: emotion_intensity, confidence: confidence})[0..$max_items] AS items
    RETURN type, items  
      `,
      {
        query_embedding: queryEmbedding,
        similarity_threshold: similarityThreshold,
        query_date_range: queryDateRange,
        max_items: Math.max(maxEvents, maxClaims),
        recent_coeff: 0.33,
        historic_coeff: 50,
        default_coeff: 5,
      },
      { database: 'neo4j' }
    );

    console.log(`Query parameters:`, {
      queryEmbedding: queryEmbedding.slice(0, 5) + '...', // Show first 5 elements
      similarityThreshold,
      queryDateRange,
      maxEvents,
      maxClaims
    });

    console.log(
      `The query returned ${records.length} records in ${summary.resultAvailableAfter} ms.`
    );

    const events = [];
    const claims = [];

    for (const record of records) {
      const itemType = record.get('type');
      const items = record.get('items');

      console.log(`Retrieved ${items.length} ${itemType}s`);

      for (const item of items) {
        const properties = item.node.properties;
        properties.type = itemType;
        properties.similarity = item.similarity;
        properties.time_relevance = item.time_relevance;
        properties.combined_score = item.score;
        properties.start_date = item.start_date;
        properties.years_ago = item.years_ago;

        if (itemType === 'Event') {
          properties.emotion = item.emotion;
          properties.emotion_intensity = item.emotion_intensity;
          events.push(properties);
        } else {
          properties.confidence = item.confidence;
          claims.push(properties);
        }
      }
    }

    console.log(`Processed ${events.length} events and ${claims.length} claims`);

    return {
      events: events.slice(0, maxEvents),
      claims: claims.slice(0, maxClaims),
    };
  } catch (error) {
    console.error('Error in getRelevantEventsAndClaims:', error);
    throw handleError(error, 'getRelevantEventsAndClaims');
  }
}

export async function getRelevantConceptRelationships(
  keyConcepts: string[],
  maxRelationships = 7
): Promise<{ concepts: any[], relationships: any[] }> {
  const driver = await getDriver();

  try {
    const { records, summary } = await driver.executeQuery(
      `
        UNWIND $keyConcepts AS key_concept
        MATCH (concept:Concept {name: key_concept})
        WITH COLLECT(DISTINCT concept) AS relevant_concepts
        UNWIND relevant_concepts AS concept1
        MATCH (concept1)-[relationship]-(concept2:Concept)
        WITH concept1, concept2, relationship
        ORDER BY concept1.name, concept2.name, type(relationship)
        WITH concept1, collect({
            concept1: concept1 {.name, .description},
            concept2: concept2 {.name, .description},
            relationship: type(relationship)
        })[0..$maxRelationships] AS limited_relationships
        UNWIND limited_relationships AS rel
        RETURN 
            rel.concept1.name AS source_name,
            rel.concept1.description AS source_description,
            rel.concept2.name AS target_name,
            rel.concept2.description AS target_description,
            rel.relationship AS relationship_type
      `,
      { keyConcepts, maxRelationships },
      { database: 'neo4j' }
    );

    console.log(`Query parameters:`, { keyConcepts, maxRelationships });

    console.log(
      `The query returned ${records.length} records in ${summary.resultAvailableAfter} ms.`
    );

    const concepts: { [key: string]: any } = {};
    const relationships: any[] = [];

    for (const record of records) {
      const sourceName = record.get('source_name');
      const targetName = record.get('target_name');
      const relationshipType = record.get('relationship_type');

      if (!concepts[sourceName]) {
        concepts[sourceName] = { name: sourceName, description: record.get('source_description') };
      }
      if (targetName && !concepts[targetName]) {
        concepts[targetName] = { name: targetName, description: record.get('target_description') };
      }

      if (targetName && relationshipType) {
        relationships.push({
          source: sourceName,
          target: targetName,
          type: relationshipType,
        });
      }
    }

    console.log(`Processed ${Object.keys(concepts).length} concepts and ${relationships.length} relationships`);

    return {
      concepts: Object.values(concepts),
      relationships,
    };
  } catch (error) {
    console.error('Error in getRelevantConceptRelationships:', error);
    throw handleError(error, 'getRelevantConceptRelationships');
  }
}