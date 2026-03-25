// AetherionBUE iOS SDK
// Version: 2.0.0

import Foundation
import Combine

@available(iOS 13.0, *)
public class AetherionBUE {
    private let apiKey: String
    private let baseURL: URL
    private let session: URLSession
    
    public init(apiKey: String, baseURL: String = "https://api.aetherion.ai/bue") {
        self.apiKey = apiKey
        self.baseURL = URL(string: baseURL)!
        
        let config = URLSessionConfiguration.default
        config.httpAdditionalHeaders = [
            "Authorization": "Bearer \(apiKey)",
            "Content-Type": "application/json"
        ]
        self.session = URLSession(configuration: config)
    }
    
    public func analyze(deal: [String: Any], assetType: AssetType, options: AnalysisOptions = AnalysisOptions()) async throws -> AnalysisResult {
        let endpoint = baseURL.appendingPathComponent("/v1/analyze")
        let payload: [String: Any] = [
            "asset_type": assetType.rawValue,
            "data": deal,
            "options": options.toDictionary()
        ]
        
        let data = try JSONSerialization.data(withJSONObject: payload)
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.httpBody = data
        
        let (responseData, _) = try await session.data(for: request)
        let result = try JSONDecoder().decode(AnalysisResult.self, from: responseData)
        
        return result
    }
}

public enum AssetType: String, Codable {
    case saas = "saas"
    case cre = "cre"
}

public struct AnalysisOptions: Codable {
    public var enableMonteCarlo: Bool = true
    public var simulations: Int = 10_000
    public init() {}
    
    func toDictionary() -> [String: Any] {
        return ["enable_monte_carlo": enableMonteCarlo, "simulations": simulations]
    }
}

public struct AnalysisResult: Codable {
    public let id: String
    public let score: Double
    public let rating: String
    public let executionTimeMs: Double
}
