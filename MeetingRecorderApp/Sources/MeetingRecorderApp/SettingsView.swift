import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var networkManager: NetworkManager
    @EnvironmentObject var audioManager: AudioManager
    
    @State private var serverURL: String = ""
    @State private var isTestingConnection = false
    @State private var connectionTestResult: String?
    @State private var showingAdvanced = false
    
    var body: some View {
        Form {
            Section(header: Text("Server Configuration")) {
                HStack {
                    Text("Server URL:")
                    TextField("http://192.168.31.58:9000", text: $serverURL)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .onChange(of: serverURL) { newValue in
                            networkManager.updateServerURL(newValue)
                        }
                }
                
                HStack {
                    Button("Test Connection") {
                        testConnection()
                    }
                    .disabled(isTestingConnection || serverURL.isEmpty)
                    
                    if isTestingConnection {
                        ProgressView()
                            .scaleEffect(0.7)
                    }
                    
                    Spacer()
                    
                    if let result = connectionTestResult {
                        Text(result)
                            .foregroundColor(result.contains("✅") ? .green : .red)
                    }
                }
            }
            
            Section(header: Text("Recording Settings")) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Audio Quality: High (16kHz, 16-bit, Mono)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text("Optimized for Whisper.cpp transcription")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Toggle("Auto-process recordings", isOn: .constant(true))
                    .disabled(true) // Always enabled for now
                
                Toggle("Show progress notifications", isOn: .constant(true))
                    .disabled(true) // Always enabled for now
            }
            
            Section(header: Text("Advanced")) {
                DisclosureGroup("Advanced Settings", isExpanded: $showingAdvanced) {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Network timeout:")
                            Spacer()
                            Text("30 seconds")
                                .foregroundColor(.secondary)
                        }
                        
                        HStack {
                            Text("Audio format:")
                            Spacer()
                            Text("WAV (PCM)")
                                .foregroundColor(.secondary)
                        }
                        
                        HStack {
                            Text("Temp file cleanup:")
                            Spacer()
                            Text("Automatic")
                                .foregroundColor(.secondary)
                        }
                    }
                    .font(.caption)
                }
            }
            
            Section(header: Text("About")) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("Version:")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Build:")
                        Spacer()
                        Text("2024.01")
                            .foregroundColor(.secondary)
                    }
                    
                    Button("Check for Updates") {
                        // Trigger Sparkle update check
                        checkForUpdates()
                    }
                }
                .font(.caption)
            }
            
            Section {
                VStack(spacing: 8) {
                    Button("Reset to Defaults") {
                        resetToDefaults()
                    }
                    .foregroundColor(.red)
                    
                    Button("Export Logs") {
                        exportLogs()
                    }
                }
            }
        }
        .navigationTitle("Settings")
        .frame(width: 500, height: 400)
        .onAppear {
            serverURL = networkManager.serverURL
        }
    }
    
    private func testConnection() {
        isTestingConnection = true
        connectionTestResult = nil
        
        Task {
            let isHealthy = await networkManager.checkServerHealth()
            
            await MainActor.run {
                isTestingConnection = false
                connectionTestResult = isHealthy ? "✅ Connected" : "❌ Failed"
            }
        }
    }
    
    private func resetToDefaults() {
        serverURL = "http://192.168.31.58:9000"
        networkManager.updateServerURL(serverURL)
        connectionTestResult = nil
    }
    
    private func exportLogs() {
        // Export app logs for debugging
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = "MeetingRecorder_logs_\(Date().timeIntervalSince1970).txt"
        savePanel.allowedContentTypes = [.plainText]
        
        if savePanel.runModal() == .OK {
            guard let url = savePanel.url else { return }
            
            let logs = "Meeting Recorder Logs\n" +
                     "Version: 1.0.0\n" +
                     "Server URL: \(serverURL)\n" +
                     "Date: \(Date())\n" +
                     "Audio Engine: AVAudioEngine\n" +
                     "Network: URLSession + WebSocket\n"
            
            try? logs.write(to: url, atomically: true, encoding: .utf8)
        }
    }
    
    private func checkForUpdates() {
        // Trigger Sparkle framework update check
        if NSApp.delegate is AppDelegate {
            // This would call the updater
            print("Checking for updates...")
        }
    }
}

// Preview for SwiftUI Canvas
struct SettingsView_Previews: PreviewProvider {
    static var previews: some View {
        SettingsView()
            .environmentObject(NetworkManager.shared)
            .environmentObject(AudioManager.shared)
    }
} 