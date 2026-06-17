export type ScoreTier = "high" | "medium" | "low"

export function getScoreTier(score: number): ScoreTier {
  if (score >= 70) return "high"
  if (score >= 40) return "medium"
  return "low"
}

export function getScoreBadgeClass(score: number): string {
  const tier = getScoreTier(score)
  if (tier === "high") {
    return "bg-emerald-600 text-white"
  }
  if (tier === "medium") {
    return "bg-amber-500 text-white"
  }
  return "bg-red-500 text-white"
}

export function formatScore(score: number): string {
  return Math.min(100, Math.max(0, score)).toFixed(1)
}
