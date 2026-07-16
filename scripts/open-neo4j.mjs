#!/usr/bin/env node
import { execSync } from "node:child_process"
import { fileURLToPath } from "node:url"
import path from "node:path"

const NEO4J_URL = "http://localhost:7474"
const CONTAINER_NAME = "productgpt-neo4j"
const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")

function run(command, options = {}) {
  return execSync(command, {
    cwd: PROJECT_ROOT,
    encoding: "utf8",
    stdio: options.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
    ...options,
  })
}

function isNeo4jRunning() {
  try {
    const names = run(
      `docker ps --filter name=${CONTAINER_NAME} --filter status=running --format "{{.Names}}"`,
    ).trim()
    return names.includes(CONTAINER_NAME)
  } catch {
    return false
  }
}

function startNeo4j() {
  console.log("Starting Neo4j via docker compose...")
  run("docker compose up -d neo4j", { inherit: true })
}

async function waitForNeo4j(maxAttempts = 45) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(NEO4J_URL, { redirect: "follow" })
      if (response.ok || response.status < 500) {
        return true
      }
    } catch {
      // Neo4j still booting
    }
    process.stdout.write(".")
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  process.stdout.write("\n")
  return false
}

function openBrowser(url) {
  const platform = process.platform
  if (platform === "darwin") {
    run(`open "${url}"`)
    return
  }
  if (platform === "win32") {
    run(`start "" "${url}"`, { shell: true })
    return
  }
  run(`xdg-open "${url}"`)
}

if (!isNeo4jRunning()) {
  startNeo4j()
  console.log("Waiting for Neo4j Browser")
  const ready = await waitForNeo4j()
  if (!ready) {
    console.warn("Neo4j may still be starting. Opening the browser anyway.")
  } else {
    console.log("\nNeo4j is ready.")
  }
}

console.log(`Opening Neo4j Browser at ${NEO4J_URL}`)
console.log("Login: neo4j / productgpt")
openBrowser(NEO4J_URL)
