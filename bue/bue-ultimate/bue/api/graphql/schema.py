"""GraphQL Schema for BUE Ultimate API"""

SCHEMA = """
scalar DateTime
scalar JSON

type Analysis {
  id: ID!
  timestamp: DateTime!
  assetType: String!
  mode: String!
  score: Float!
  rating: String!
  metrics: JSON!
  riskAnalysis: JSON
  forecast: JSON
  governance: JSON
  executionTimeMs: Float!
  deviceCount: Int
  gpuUtilized: Boolean!
}

input AnalysisInput {
  assetType: String!
  data: JSON!
  options: JSON
}

type Query {
  analysis(id: ID!): Analysis
  health: JSON!
}

type Mutation {
  analyze(input: AnalysisInput!): Analysis!
}

type Subscription {
  analysisProgress(analysisId: ID!): JSON!
}
"""

def get_schema() -> str:
    return SCHEMA
