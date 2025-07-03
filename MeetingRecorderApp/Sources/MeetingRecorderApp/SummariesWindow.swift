import Cocoa
import SwiftUI
import UserNotifications

class SummariesWindow: NSWindowController {
    convenience init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 400),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "Recent Meeting Summaries"
        window.center()
        
        let summariesView = SummariesView()
        window.contentView = NSHostingView(rootView: summariesView)
        
        self.init(window: window)
    }
}

struct SummariesView: View {
    @StateObject private var networkManager = NetworkManager.shared
    @State private var transcriptionHistory: [TranscriptionHistory] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    VStack(spacing: 16) {
                        ProgressView()
                            .scaleEffect(1.5)
                        
                        Text("Loading history...")
                            .font(.headline)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.red)
                        
                        Text("Error Loading History")
                            .font(.headline)
                        
                        Text(errorMessage)
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Button("Retry") {
                            loadHistory()
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if transcriptionHistory.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "doc.text")
                            .font(.largeTitle)
                            .foregroundColor(.secondary)
                        
                        Text("No Recordings Yet")
                            .font(.headline)
                        
                        Text("Start recording meetings to see transcriptions here")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(transcriptionHistory) { item in
                        TranscriptionRowView(transcription: item)
                    }
                }
            }
            .navigationTitle("Meeting History")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Refresh") {
                        loadHistory()
                    }
                }
            }
        }
        .onAppear {
            loadHistory()
        }
    }
    
    private func loadHistory() {
        isLoading = true
        errorMessage = nil
        
        Task {
            let result = await networkManager.fetchRecentSummaries()
            
            await MainActor.run {
                isLoading = false
                
                switch result {
                case .success(let fetchedHistory):
                    transcriptionHistory = fetchedHistory
                case .failure(let error):
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}

struct TranscriptionRowView: View {
    let transcription: TranscriptionHistory
    @State private var isDownloading = false
    
    private let networkManager = NetworkManager.shared
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(transcription.filename)
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Spacer()
                
                Text(formatDate(transcription.createdAt))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            HStack {
                Text("Size: \(formatFileSize(transcription.fileSize))")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                if transcription.hasSummary {
                    Label("Summary Available", systemImage: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundColor(.green)
                } else {
                    Label("Transcription Only", systemImage: "doc.text")
                        .font(.caption)
                        .foregroundColor(.orange)
                }
            }
            
            HStack(spacing: 8) {
                Button(action: {
                    downloadTranscription()
                }) {
                    HStack(spacing: 4) {
                        if isDownloading {
                            ProgressView()
                                .scaleEffect(0.7)
                        } else {
                            Image(systemName: "doc.text")
                        }
                        Text("Transcription")
                    }
                }
                .disabled(isDownloading)
                .buttonStyle(.bordered)
                
                if transcription.hasSummary {
                    Button(action: {
                        downloadSummary()
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "doc.richtext")
                            Text("Summary")
                        }
                    }
                    .disabled(isDownloading)
                    .buttonStyle(.bordered)
                } else {
                    Button(action: {
                        generateSummary()
                    }) {
                        HStack(spacing: 4) {
                            if isDownloading {
                                ProgressView()
                                    .scaleEffect(0.7)
                            } else {
                                Image(systemName: "doc.richtext.fill")
                            }
                            Text("Generate Summary")
                        }
                    }
                    .disabled(isDownloading)
                    .buttonStyle(.borderedProminent)
                }
                
                Spacer()
            }
        }
        .padding(.vertical, 8)
    }
    
    private func downloadTranscription() {
        isDownloading = true
        
        Task {
            let result = await networkManager.downloadTranscription(transcriptionId: transcription.id)
            
            await MainActor.run {
                isDownloading = false
                
                switch result {
                case .success(let content):
                    saveFile(content: content, filename: "transcript_\(transcription.id).txt")
                case .failure(let error):
                    showErrorAlert(error.localizedDescription)
                }
            }
        }
    }
    
    private func downloadSummary() {
        isDownloading = true
        
        Task {
            let result = await networkManager.downloadSummary(transcriptionId: transcription.id)
            
            await MainActor.run {
                isDownloading = false
                
                switch result {
                case .success(let content):
                    saveFile(content: content, filename: "summary_\(transcription.id).txt")
                case .failure(let error):
                    showErrorAlert(error.localizedDescription)
                }
            }
        }
    }
    
    private func generateSummary() {
        isDownloading = true
        
        Task {
            // First, download the transcription
            let transcriptionResult = await networkManager.downloadTranscription(transcriptionId: transcription.id)
            
            switch transcriptionResult {
            case .success(let transcriptionText):
                // Now generate the summary
                let summaryResult = await networkManager.generateSummary(transcription: transcriptionText, transcriptionId: transcription.id)
                
                await MainActor.run {
                    isDownloading = false
                    
                    switch summaryResult {
                    case .success(let summary):
                        // Save the summary file and show success
                        saveFile(content: summary, filename: "summary_\(transcription.id).txt")
                        
                        // Show success notification
                        let content = UNMutableNotificationContent()
                        content.title = "Summary Generated"
                        content.body = "Summary created for \(transcription.filename)"
                        content.sound = UNNotificationSound.default
                        
                        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
                        UNUserNotificationCenter.current().add(request) { error in
                            if let error = error {
                                print("Failed to show notification: \(error)")
                            }
                        }
                        
                    case .failure(let error):
                        showErrorAlert("Failed to generate summary: \(error.localizedDescription)")
                    }
                }
                
            case .failure(let error):
                await MainActor.run {
                    isDownloading = false
                    showErrorAlert("Failed to download transcription: \(error.localizedDescription)")
                }
            }
        }
    }
    
    private func saveFile(content: String, filename: String) {
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = filename
        savePanel.allowedContentTypes = [.plainText]
        
        if savePanel.runModal() == .OK {
            guard let url = savePanel.url else { return }
            
            do {
                try content.write(to: url, atomically: true, encoding: .utf8)
                
                // Show success notification
                let content = UNMutableNotificationContent()
                content.title = "File Downloaded"
                content.body = "Saved to \(url.lastPathComponent)"
                content.sound = UNNotificationSound.default
                
                let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
                UNUserNotificationCenter.current().add(request) { error in
                    if let error = error {
                        print("Failed to show notification: \(error)")
                    }
                }
                
            } catch {
                showErrorAlert("Failed to save file: \(error.localizedDescription)")
            }
        }
    }
    
    private func showErrorAlert(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Download Failed"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        
        if let date = formatter.date(from: dateString) {
            formatter.dateStyle = .medium
            formatter.timeStyle = .short
            return formatter.string(from: date)
        }
        
        return dateString
    }
    
    private func formatFileSize(_ size: Int) -> String {
        let sizeInKB = Double(size) / 1024
        let sizeInMB = sizeInKB / 1024
        
        if sizeInMB > 1 {
            return "\(String(format: "%.2f", sizeInMB)) MB"
        } else if sizeInKB > 1 {
            return "\(String(format: "%.2f", sizeInKB)) KB"
        } else {
            return "\(size) bytes"
        }
    }
}

struct SummariesView_Previews: PreviewProvider {
    static var previews: some View {
        SummariesView()
    }
} 