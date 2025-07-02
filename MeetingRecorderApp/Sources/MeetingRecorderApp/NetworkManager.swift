import Foundation
// import Starscream // Temporarily disabled

class NetworkManager: ObservableObject {
    static let shared = NetworkManager()
    
    @Published var serverURL: String = "http://192.168.31.58:9000"  // DietPi server
    @Published var isConnected = false
    
    // private var socket: WebSocket? // Temporarily disabled
    private var currentSessionId: String?
    
    var onProgressUpdate: ((Double, String) -> Void)?
    var onTranscriptionChunk: ((String) -> Void)?
    
    private init() {
        loadSettings()
    }
    
    // MARK: - Settings Management
    
    private func loadSettings() {
        if let savedURL = UserDefaults.standard.string(forKey: "serverURL") {
            serverURL = savedURL
        }
    }
    
    func updateServerURL(_ url: String) {
        serverURL = url
        UserDefaults.standard.set(url, forKey: "serverURL")
    }
    
    // MARK: - Audio Upload
    
    func uploadAudio(fileURL: URL) async -> Result<UploadResponse, Error> {
        guard let uploadURL = URL(string: "\(serverURL)/upload") else {
            return .failure(NetworkError.invalidURL)
        }
        
        do {
            let audioData = try Data(contentsOf: fileURL)
            
            var request = URLRequest(url: uploadURL)
            request.httpMethod = "POST"
            
            let boundary = UUID().uuidString
            request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
            
            let body = createMultipartBody(data: audioData, filename: fileURL.lastPathComponent, boundary: boundary)
            request.httpBody = body
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return .failure(NetworkError.serverError)
            }
            
            let result = try JSONDecoder().decode(UploadResponse.self, from: data)
            
            if let error = result.error {
                return .failure(NetworkError.customError(error))
            }
            
            return .success(result)
            
        } catch {
            return .failure(error)
        }
    }
    
    private func createMultipartBody(data: Data, filename: String, boundary: String) -> Data {
        var body = Data()
        
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        return body
    }
    
    // MARK: - WebSocket Connection (Temporarily Disabled)
    
    /*
    private func connectWebSocket(sessionId: String) {
        guard let socketURL = URL(string: serverURL.replacingOccurrences(of: "http", with: "ws")) else { return }
        
        var request = URLRequest(url: socketURL)
        request.timeoutInterval = 30
        
        socket = WebSocket(request: request)
        socket?.delegate = self
        socket?.connect()
        
        // Join session for progress updates
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            self.joinSession(sessionId: sessionId)
        }
    }
    
    private func joinSession(sessionId: String) {
        let message = [
            "session_id": sessionId
        ]
        
        if let data = try? JSONSerialization.data(withJSONObject: message),
           let string = String(data: data, encoding: .utf8) {
            socket?.write(string: "join_session:\(string)")
        }
    }
    */
    
    // MARK: - Health Check
    
    func checkServerHealth() async -> Bool {
        guard let healthURL = URL(string: "\(serverURL)/health") else { return false }
        
        do {
            let (_, response) = try await URLSession.shared.data(from: healthURL)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
    
    // MARK: - Recent Summaries
    
    func fetchRecentSummaries() async -> Result<[TranscriptionHistory], Error> {
        guard let historyURL = URL(string: "\(serverURL)/history") else {
            return .failure(NetworkError.invalidURL)
        }
        
        do {
            let (data, _) = try await URLSession.shared.data(from: historyURL)
            let history = try JSONDecoder().decode([TranscriptionHistory].self, from: data)
            return .success(history)
        } catch {
            return .failure(error)
        }
    }
    
    func downloadTranscription(transcriptionId: Int) async -> Result<String, Error> {
        guard let downloadURL = URL(string: "\(serverURL)/download/transcription/\(transcriptionId)") else {
            return .failure(NetworkError.invalidURL)
        }
        
        do {
            let (data, _) = try await URLSession.shared.data(from: downloadURL)
            let transcription = String(data: data, encoding: .utf8) ?? ""
            return .success(transcription)
        } catch {
            return .failure(error)
        }
    }
    
    func downloadSummary(transcriptionId: Int) async -> Result<String, Error> {
        guard let downloadURL = URL(string: "\(serverURL)/download/summary/\(transcriptionId)") else {
            return .failure(NetworkError.invalidURL)
        }
        
        do {
            let (data, _) = try await URLSession.shared.data(from: downloadURL)
            let summary = String(data: data, encoding: .utf8) ?? ""
            return .success(summary)
        } catch {
            return .failure(error)
        }
    }
    
    // MARK: - Generate Summary
    
    func generateSummary(transcription: String, transcriptionId: Int) async -> Result<String, Error> {
        guard let summaryURL = URL(string: "\(serverURL)/summarize") else {
            return .failure(NetworkError.invalidURL)
        }
        
        do {
            var request = URLRequest(url: summaryURL)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            
            let body = [
                "transcription": transcription,
                "transcription_id": transcriptionId
            ] as [String : Any]
            
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return .failure(NetworkError.serverError)
            }
            
            let result = try JSONDecoder().decode(SummaryResponse.self, from: data)
            
            if let error = result.error {
                return .failure(NetworkError.customError(error))
            }
            
            return .success(result.summary ?? "Summary generated")
            
        } catch {
            return .failure(error)
        }
    }
}

// MARK: - WebSocket Delegate (Temporarily Disabled)

/*
extension NetworkManager: WebSocketDelegate {
    func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        switch event {
        case .connected(let headers):
            print("WebSocket connected: \(headers)")
            isConnected = true
            
        case .disconnected(let reason, let code):
            print("WebSocket disconnected: \(reason) with code: \(code)")
            isConnected = false
            
        case .text(let string):
            handleWebSocketMessage(string)
            
        case .binary(let data):
            print("Received binary data: \(data.count) bytes")
            
        case .error(let error):
            print("WebSocket error: \(error?.localizedDescription ?? "Unknown error")")
            
        case .cancelled:
            print("WebSocket cancelled")
            isConnected = false
            
        default:
            break
        }
    }
    
    private func handleWebSocketMessage(_ message: String) {
        guard let data = message.data(using: .utf8) else { return }
        
        if let progressUpdate = try? JSONDecoder().decode(ProgressUpdate.self, from: data) {
            DispatchQueue.main.async {
                self.onProgressUpdate?(progressUpdate.progress, progressUpdate.message)
                
                // Handle real-time transcription chunks
                if let chunk = progressUpdate.transcriptionChunk {
                    self.onTranscriptionChunk?(chunk.text)
                }
            }
        }
    }
}
*/

// MARK: - Data Models

struct UploadResponse: Codable {
    let success: Bool
    let transcription: String?
    let filename: String?
    let transcriptionId: Int?
    let downloadUrl: String?
    let analysis: LanguageAnalysis?
    let error: String?
    
    enum CodingKeys: String, CodingKey {
        case success, transcription, filename, analysis, error
        case transcriptionId = "transcription_id"
        case downloadUrl = "download_url"
    }
}

struct SummaryResponse: Codable {
    let success: Bool
    let summary: String?
    let downloadUrl: String?
    let error: String?
    
    enum CodingKeys: String, CodingKey {
        case success, summary, error
        case downloadUrl = "download_url"
    }
}

struct LanguageAnalysis: Codable {
    let language: String
    let quality: String
    let totalWords: Int
    let uniqueWords: Int
    let repetitionRatio: Double
    let tamilWordsDetected: Int?
    let englishWordsDetected: Int?
    
    enum CodingKeys: String, CodingKey {
        case language, quality, repetitionRatio
        case totalWords = "total_words"
        case uniqueWords = "unique_words"
        case tamilWordsDetected = "tamil_words_detected"
        case englishWordsDetected = "english_words_detected"
    }
}

struct TranscriptionHistory: Codable, Identifiable {
    let id: Int
    let filename: String
    let createdAt: String
    let fileSize: Int
    let hasSummary: Bool
    let transcriptionUrl: String
    let summaryUrl: String?
    
    enum CodingKeys: String, CodingKey {
        case id, filename
        case createdAt = "created_at"
        case fileSize = "file_size"
        case hasSummary = "has_summary"
        case transcriptionUrl = "transcription_url"
        case summaryUrl = "summary_url"
    }
}

// Legacy models - kept for compatibility
struct Summary: Codable, Identifiable {
    let id: Int
    let summary: String
    let tag: String?
    let createdAt: String
    
    enum CodingKeys: String, CodingKey {
        case id, summary, tag
        case createdAt = "created_at"
    }
}

struct ProgressUpdate: Codable {
    let sessionId: String
    let stage: String
    let progress: Double
    let message: String
    let transcriptionChunk: TranscriptionChunk?
    
    enum CodingKeys: String, CodingKey {
        case stage, progress, message
        case sessionId = "session_id"
        case transcriptionChunk = "transcription_chunk"
    }
}

struct TranscriptionChunk: Codable {
    let timestamp: String
    let text: String
    let chunkNumber: Int?
    
    enum CodingKeys: String, CodingKey {
        case timestamp, text
        case chunkNumber = "chunk_number"
    }
}

enum NetworkError: Error, LocalizedError {
    case invalidURL
    case serverError
    case noData
    case customError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid server URL"
        case .serverError:
            return "Server error occurred"
        case .noData:
            return "No data received"
        case .customError(let message):
            return message
        }
    }
} 