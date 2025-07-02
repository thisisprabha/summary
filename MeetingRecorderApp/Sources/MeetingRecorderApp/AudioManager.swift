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
    private var hasPermission = false
    
    // Callbacks for UI updates
    var onRecordingStateChanged: ((Bool) -> Void)?
    var onProcessingStateChanged: ((Bool) -> Void)?
    var onSummaryReceived: ((String) -> Void)?
    var onProgressUpdate: ((Double, String) -> Void)?
    
    private let networkManager = NetworkManager.shared
    
    private init() {
        setupAudioEngine()
        requestMicrophonePermission()
    }
    
    private func setupAudioEngine() {
        // Create audio engine once and reuse it
        audioEngine = AVAudioEngine()
        print("🔊 Audio engine initialized for speech recognition")
    }
    
    private func requestMicrophonePermission() {
        // Check current permission status
        let status = AVCaptureDevice.authorizationStatus(for: .audio)
        
        switch status {
        case .authorized:
            hasPermission = true
            print("✅ Microphone permission already granted")
            
        case .notDetermined:
            // Request permission only if not determined
            AVCaptureDevice.requestAccess(for: .audio) { [weak self] granted in
                DispatchQueue.main.async {
                    self?.hasPermission = granted
                    if granted {
                        print("✅ Microphone permission granted")
                    } else {
                        print("❌ Microphone permission denied")
                    }
                }
            }
            
        case .denied, .restricted:
            hasPermission = false
            print("❌ Microphone permission denied or restricted")
            showPermissionAlert()
            
        @unknown default:
            hasPermission = false
            print("❓ Unknown microphone permission status")
        }
    }
    
    private func showPermissionAlert() {
        let content = UNMutableNotificationContent()
        content.title = "Microphone Permission Required"
        content.body = "Please enable microphone access in System Preferences > Security & Privacy > Privacy > Microphone"
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }
    
    func startRecording() {
        guard !isRecording else { return }
        
        // Check permission before starting
        guard hasPermission else {
            print("❌ Cannot start recording: Microphone permission not granted")
            requestMicrophonePermission() // Try to request again
            return
        }
        
        do {
            // Create temporary file for recording - use m4a format like Voice Memo
            let tempDir = FileManager.default.temporaryDirectory
            recordingURL = tempDir.appendingPathComponent("meeting_\(Date().timeIntervalSince1970).m4a")
            
            guard let recordingURL = recordingURL else { return }
            guard let audioEngine = audioEngine else { return }
            
            // Stop engine if it's running (cleanup from previous session)
            if audioEngine.isRunning {
                audioEngine.stop()
                audioEngine.inputNode.removeTap(onBus: 0)
            }
            
            let inputNode = audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            
            // Enhanced audio settings optimized for Tamil/English speech recognition
            // Using AAC format like Voice Memo for better compression and quality
            let settings: [String: Any] = [
                AVFormatIDKey: kAudioFormatMPEG4AAC,  // Same as Voice Memo
                AVSampleRateKey: 44100.0,             // High quality sample rate
                AVNumberOfChannelsKey: 1,             // Mono for speech
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
                AVEncoderBitRateKey: 128000,          // Good quality bitrate
                AVAudioFileTypeKey: kAudioFileM4AType // M4A container
            ]
            
            audioFile = try AVAudioFile(forWriting: recordingURL, settings: settings)
            
            // Use larger buffer for better quality - especially important for Tamil speech
            inputNode.installTap(onBus: 0, bufferSize: 4096, format: recordingFormat) { [weak self] buffer, time in
                do {
                    // Convert to the target format if needed
                    try self?.audioFile?.write(from: buffer)
                } catch {
                    print("Error writing audio buffer: \(error)")
                }
            }
            
            // Start recording
            try audioEngine.start()
            isRecording = true
            onRecordingStateChanged?(true)
            
            print("🎤 Started recording with optimized Tamil/English settings")
            
        } catch {
            print("Failed to start recording: \(error)")
            stopRecording()
        }
    }
    
    func stopRecording() {
        guard isRecording else { return }
        
        // Properly stop the audio engine without destroying it
        if let audioEngine = audioEngine, audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        
        audioFile = nil
        isRecording = false
        
        onRecordingStateChanged?(false)
        onProcessingStateChanged?(true)
        
        print("🎤 Stopped recording, processing with enhanced Tamil support...")
        
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
                    case .success(let uploadResponse):
                        // Show transcription preview with enhanced language info
                        var message = "✅ Transcription complete!"
                        
                        if let analysis = uploadResponse.analysis {
                            message += " 🌐 Language: \(analysis.language)"
                            if let tamil = analysis.tamilWordsDetected, tamil > 0 {
                                message += " 🔤 Tamil: \(tamil) words"
                            }
                            if let english = analysis.englishWordsDetected, english > 0 {
                                message += " 🔤 English: \(english) words"
                            }
                        }
                        
                        // Use transcription preview as summary for now
                        let transcriptionPreview = uploadResponse.transcription?.prefix(300) ?? "Transcription processed"
                        self.onSummaryReceived?(String(transcriptionPreview))
                        
                        // Optionally generate full summary
                        if let transcription = uploadResponse.transcription,
                           let transcriptionId = uploadResponse.transcriptionId {
                            self.generateSummary(transcription: transcription, transcriptionId: transcriptionId)
                        }
                        
                    case .failure(let error):
                        print("Upload failed: \(error)")
                        self.showErrorNotification(error.localizedDescription)
                    }
                }
                
                // Clean up temporary file
                try? FileManager.default.removeItem(at: url)
                
            }
        }
    }
    
    private func generateSummary(transcription: String, transcriptionId: Int) {
        Task {
            let result = await networkManager.generateSummary(transcription: transcription, transcriptionId: transcriptionId)
            
            DispatchQueue.main.async {
                switch result {
                case .success(let summary):
                    // Update with full summary
                    self.onSummaryReceived?(summary)
                case .failure(let error):
                    print("Summary generation failed: \(error)")
                    // Keep the transcription preview as fallback
                }
            }
        }
    }
    
    private func showErrorNotification(_ message: String) {
        let content = UNMutableNotificationContent()
        content.title = "Meeting Recorder"
        content.body = message
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Failed to show notification: \(error)")
            }
        }
    }
    
    // MARK: - Enhanced Audio Quality Settings
    
    func getOptimalRecordingSettings() -> [String: Any] {
        // Voice Memo compatible settings for best Tamil/English transcription
        return [
            AVFormatIDKey: kAudioFormatMPEG4AAC,      // AAC like Voice Memo
            AVSampleRateKey: 44100.0,                 // High quality
            AVNumberOfChannelsKey: 1,                 // Mono for speech
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
            AVEncoderBitRateKey: 128000,              // 128 kbps
            AVAudioFileTypeKey: kAudioFileM4AType     // M4A container
        ]
    }
    
    // MARK: - macOS Audio Configuration
    
    private func configureMacOSAudioForSpeech() {
        // macOS-specific audio configuration for optimal speech recording
        // No AVAudioSession needed on macOS - AVAudioEngine handles it
        print("🔊 macOS audio configured for speech recognition")
    }
    
    // MARK: - Recording State
    
    var recordingState: Bool {
        return isRecording
    }
    
    func getCurrentRecordingDuration() -> TimeInterval {
        guard isRecording, let audioFile = audioFile else { return 0 }
        return Double(audioFile.length) / audioFile.fileFormat.sampleRate
    }
    
    // MARK: - Quality Diagnostics
    
    func getAudioQualityInfo() -> String {
        guard let audioFile = audioFile else { return "No active recording" }
        
        let format = audioFile.fileFormat
        return """
        📊 Audio Quality:
        • Format: \(format.formatDescription)
        • Sample Rate: \(format.sampleRate) Hz
        • Channels: \(format.channelCount)
        • Duration: \(String(format: "%.1f", getCurrentRecordingDuration()))s
        """
    }
    
    // MARK: - Cleanup
    
    deinit {
        cleanup()
    }
    
    private func cleanup() {
        if let audioEngine = audioEngine, audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        audioEngine = nil
        audioFile = nil
    }
    
    // MARK: - Permission Status
    
    func checkMicrophonePermission() -> Bool {
        let status = AVCaptureDevice.authorizationStatus(for: .audio)
        return status == .authorized
    }
} 