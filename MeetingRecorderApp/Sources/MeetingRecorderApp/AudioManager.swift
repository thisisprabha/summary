import Foundation
import AVFoundation
import CoreAudio
import UserNotifications

class AudioManager: ObservableObject {
    static let shared = AudioManager()
    
    private var audioEngine: AVAudioEngine?
    private var audioFile: AVAudioFile?
    private var recordingURL: URL?
    private var isRecording = false
    
    // Callbacks for UI updates
    var onRecordingStateChanged: ((Bool) -> Void)?
    var onProcessingStateChanged: ((Bool) -> Void)?
    var onSummaryReceived: ((String) -> Void)?
    var onProgressUpdate: ((Double, String) -> Void)?
    
    private let networkManager = NetworkManager.shared
    
    private init() {
        setupAudioPermissions()
    }
    
    private func setupAudioPermissions() {
        // On macOS, microphone permissions are handled by the system
        // The Info.plist NSMicrophoneUsageDescription will trigger the permission request
    }
    
    func startRecording() {
        guard !isRecording else { return }
        
        do {
            // Create temporary file for recording
            let tempDir = FileManager.default.temporaryDirectory
            recordingURL = tempDir.appendingPathComponent("meeting_\(Date().timeIntervalSince1970).wav")
            
            guard let recordingURL = recordingURL else { return }
            
            // Setup audio engine
            audioEngine = AVAudioEngine()
            guard let audioEngine = audioEngine else { return }
            
            let inputNode = audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            
            // Create audio file with optimal settings for Whisper
            let settings: [String: Any] = [
                AVFormatIDKey: kAudioFormatLinearPCM,
                AVSampleRateKey: 16000.0,  // Optimal for Whisper
                AVNumberOfChannelsKey: 1,   // Mono
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsBigEndianKey: false
            ]
            
            audioFile = try AVAudioFile(forWriting: recordingURL, settings: settings)
            
            // Install tap to record audio
            inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, time in
                do {
                    try self?.audioFile?.write(from: buffer)
                } catch {
                    print("Error writing audio buffer: \(error)")
                }
            }
            
            // Start recording
            try audioEngine.start()
            isRecording = true
            onRecordingStateChanged?(true)
            
        } catch {
            print("Failed to start recording: \(error)")
            stopRecording()
        }
    }
    
    func stopRecording() {
        guard isRecording else { return }
        
        audioEngine?.stop()
        audioEngine?.inputNode.removeTap(onBus: 0)
        audioFile = nil
        isRecording = false
        
        onRecordingStateChanged?(false)
        onProcessingStateChanged?(true)
        
        // Upload and process the recording
        if let recordingURL = recordingURL {
            uploadRecording(url: recordingURL)
        }
    }
    
    private func uploadRecording(url: URL) {
        Task {
            do {
                let result = await networkManager.uploadAudio(fileURL: url)
                
                DispatchQueue.main.async {
                    self.onProcessingStateChanged?(false)
                    
                    switch result {
                    case .success(let summary):
                        self.onSummaryReceived?(summary)
                    case .failure(let error):
                        print("Upload failed: \(error)")
                        // Show error notification
                        self.showErrorNotification(error.localizedDescription)
                    }
                }
                
                // Clean up temporary file
                try? FileManager.default.removeItem(at: url)
                
            }
        }
    }
    
    private func showErrorNotification(_ message: String) {
        let content = UNMutableNotificationContent()
        content.title = "Recording Failed"
        content.body = message
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Failed to show notification: \(error)")
            }
        }
    }
    
    // MARK: - Audio Quality Settings
    
    func getOptimalRecordingSettings() -> [String: Any] {
        return [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: 16000.0,     // Optimal for Whisper.cpp
            AVNumberOfChannelsKey: 1,      // Mono reduces file size
            AVLinearPCMBitDepthKey: 16,   // Good quality/size balance
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
    }
    
    // MARK: - Recording State
    
    var recordingState: Bool {
        return isRecording
    }
    
    func getCurrentRecordingDuration() -> TimeInterval {
        guard isRecording, let audioFile = audioFile else { return 0 }
        return Double(audioFile.length) / audioFile.fileFormat.sampleRate
    }
} 