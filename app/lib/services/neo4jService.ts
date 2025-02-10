import neo4j, { Driver, Integer } from 'neo4j-driver';
import { config } from '../config';
import { handleError, AppError } from '../utils/errorHandler';
import { int } from 'neo4j-driver';

let driver: Driver | null;

export async function getDriver(): Promise<Driver> {
  if (!driver) {
    try {
      if (!config.neo4j.uri || !config.neo4j.user || !config.neo4j.password || !config.neo4j.database) {
        throw new Error('Neo4j configuration is incomplete');
      }
      driver = neo4j.driver(
        config.neo4j.uri,
        neo4j.auth.basic(config.neo4j.user, config.neo4j.password),
        {
          encrypted: "ENCRYPTION_ON",
          trust: "TRUST_ALL_CERTIFICATES",
          trustedCertificates: ['app/lib/public.crt'],
        }
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
    const { records } = await driver.executeQuery(
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
      { database: 'god' }
    );

    const events = [];
    const claims = [];

    for (const record of records) {
      const itemType = record.get('type');
      const items = record.get('items');

      // console.log(`Retrieved ${items.length} ${itemType}s`);

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

    // console.log(`Processed ${events.length} events and ${claims.length} claims`);

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
  queryEmbedding: number[],
  maxRelationships: Integer,
  similarityThreshold = 0.3
): Promise<{ concepts: any[], relationships: any[] }> {
  const driver = await getDriver();

  try {
    const { records } = await driver.executeQuery(
      `
        MATCH (concept1:Concept)
        WHERE concept1.embedding IS NOT NULL
        // Cosine similarity calculation
        WITH concept1,
            reduce(dot = 0.0, i IN range(0, size(concept1.embedding)-1) | dot + concept1.embedding[i] * $query_embedding[i]) /
            (sqrt(reduce(l2 = 0.0, i IN range(0, size(concept1.embedding)-1) | l2 + concept1.embedding[i]^2)) *
            sqrt(reduce(l2 = 0.0, i IN range(0, size($query_embedding)-1) | l2 + $query_embedding[i]^2))) AS similarity
        WHERE similarity >= $similarity_threshold
        WITH concept1, similarity
        ORDER BY similarity DESC
        // Find relationships
        MATCH (concept1)-[relationship]-(concept2:Concept)
        WHERE concept2.embedding IS NOT NULL
        // Collect results
        WITH concept1, concept2, relationship, similarity
        ORDER BY similarity DESC
        WITH COLLECT({
          source_name: concept1.name,
          source_description: concept1.description,
          target_name: concept2.name,
          target_description: concept2.description,
          relationship_type: type(relationship),
          similarity: similarity
        })[0..$max_items] AS items
        RETURN items
      `,
      { 
        query_embedding: queryEmbedding, 
        similarity_threshold: similarityThreshold, 
        max_items: maxRelationships
      },
      { database: 'god' }
    );
    
    // console.log(
    //   `The query returned ${records.length} records in ${summary.resultAvailableAfter} ms.`
    // );

    const concepts: { [key: string]: any } = {};
    const relationships: any[] = [];

    for (const record of records) {
      const items = record.get('items');

      for (const item of items) {
        const sourceName = item.source_name;
        const targetName = item.target_name;
        const relationshipType = item.relationship_type;
        const similarity = item.similarity;

        if (!concepts[sourceName]) {
          concepts[sourceName] = { name: sourceName, description: item.source_description };
        }
        if (targetName && !concepts[targetName]) {
          concepts[targetName] = { name: targetName, description: item.target_description };
        }

        if (targetName && relationshipType) {
          relationships.push({
            source: sourceName,
            target: targetName,
            type: relationshipType,
            similarity: similarity,
          });
        }
      }
    }

    console.log(`Processed ${Object.keys(concepts).length} concepts and ${relationships.length} relationships`);

    return {
      concepts: Object.values(concepts),
      relationships: relationships,
    };
  } catch (error) {
    console.error('Error in getRelevantConceptRelationships:', error);
    throw handleError(error, 'getRelevantConceptRelationships');
  }
}

export async function getRelevantLegalReferences(
  queryEmbedding: number[],
  similarityThreshold: number,
  maxItems: Integer
): Promise<any[]> {
  const driver = await getDriver();
  const cypherQuery = `
    CALL () {
      CALL db.index.vector.queryNodes('article_embedding', $max_items, $query_embedding) 
      YIELD node AS n, score AS similarity 
      WHERE similarity >= $similarity_threshold 
      RETURN n, similarity, 'Article' AS type
      UNION ALL
      CALL db.index.vector.queryNodes('amendment_embedding', $max_items, $query_embedding) 
      YIELD node AS n, score AS similarity 
      WHERE similarity >= $similarity_threshold 
      RETURN n, similarity, 'Amendment' AS type
      UNION ALL
      CALL db.index.vector.queryNodes('provision_embedding', $max_items, $query_embedding) 
      YIELD node AS n, score AS similarity
      WHERE similarity >= $similarity_threshold
        AND NOT n.section_title IN ['Transferred', 'Repealed', 'Omitted']
      RETURN n, similarity, 'Provision' AS type
    }
    WITH n, similarity, type
    RETURN {
      type: type,
      title: CASE WHEN type IN ['Article', 'Amendment'] THEN n.title ELSE null END,
      content: n.content,
      title_number: CASE WHEN type = 'Provision' THEN n.title_number ELSE null END,
      chapter_number: CASE WHEN type = 'Provision' THEN n.chapter_number ELSE null END,
      chapter_title: CASE WHEN type = 'Provision' THEN n.chapter_title ELSE null END,
      section_number: CASE WHEN type = 'Provision' THEN n.section_number ELSE null END,
      section_title: CASE WHEN type = 'Provision' THEN n.section_title ELSE null END,
      similarity: similarity
    } AS result
    ORDER BY similarity DESC
    LIMIT $max_items
  `;

  const params = {
    query_embedding: queryEmbedding,
    similarity_threshold: similarityThreshold,
    max_items: maxItems
  };

  try {
    const result = await driver.executeQuery(cypherQuery, params, { database: 'god' });
    return result.records.map(record => record.toObject());
  } catch (error) {
    console.error('Error executing Cypher query:', error);
    throw handleError(error, 'getRelevantLegalReferences');
  }
}

export async function executeCustomCypherQuery(
  queryEmbedding: number[],
  cypherQuery: string,
  similarityThreshold: number,
  maxItems: number
): Promise<any[]> {
  const driver = await getDriver();
  const fallbackQuery = `
    CALL db.index.vector.queryNodes('provision_embedding', $max_items, $query_embedding) 
    YIELD node AS n, score AS similarity
    WHERE similarity >= $similarity_threshold
    OPTIONAL MATCH (n)-[:MENTIONS]->(e:Entity)
    OPTIONAL MATCH (n)-[:MENTIONS]->(c:Concept)
    WITH n, similarity, collect(DISTINCT e.name) AS entities, collect(DISTINCT c.name) AS concepts
    RETURN {
        content: n.content,
        title_number: n.title_number,
        chapter_number: n.chapter_number,
        section: n.section_number,
        similarity: similarity,
        entities: entities,
        concepts: concepts
    } AS provision
    ORDER BY similarity DESC
  `;

  const params = {
    query_embedding: queryEmbedding,
    similarity_threshold: similarityThreshold,
    max_items: maxItems
  };

  try {
    const result = await driver.executeQuery(cypherQuery, params, { database: 'god' });
    if (result.records.length === 0) {
      console.log('Dynamic query returned empty response, falling back to static query');
      const fallbackResult = await driver.executeQuery(fallbackQuery, params, { database: 'god' });
      return fallbackResult.records.map(record => record.toObject());
    }
    return result.records.map(record => record.toObject());
  } catch (error) {
    console.error('Error executing custom Cypher query, falling back to static query:', error);
    const fallbackResult = await driver.executeQuery(fallbackQuery, params, { database: 'god' });
    return fallbackResult.records.map(record => record.toObject());
  }
}