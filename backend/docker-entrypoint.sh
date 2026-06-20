#!/bin/sh
set -e

if [ "${NEO4J_ENABLED:-true}" = "true" ]; then
  echo "Waiting for Neo4j at ${NEO4J_URI:-bolt://neo4j:7687}..."
  for i in $(seq 1 30); do
    if python -c "
from neo4j import GraphDatabase
import os
uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
user = os.environ.get('NEO4J_USER', 'neo4j')
password = os.environ.get('NEO4J_PASSWORD', 'productgpt')
driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
driver.close()
" 2>/dev/null; then
      echo "Neo4j is ready."
      break
    fi
    if [ "$i" -eq 30 ]; then
      echo "Neo4j not ready — starting API with in-memory graph fallback."
    fi
    sleep 2
  done
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
