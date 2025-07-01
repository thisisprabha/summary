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
    @State private var summaries: [Summary] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    
    private let networkManager = NetworkManager.shared
    
    var body: some View {
        NavigationView {
            VStack {
                if isLoading {
                    ProgressView("Loading summaries...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        
                        Text("Error Loading Summaries")
                            .font(.headline)
                        
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Button("Retry") {
                            loadSummaries()
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if summaries.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "doc.text")
                            .font(.largeTitle)
                            .foregroundColor(.secondary)
                        
                        Text("No Summaries Yet")
                            .font(.headline)
                        
                        Text("Start recording meetings to see summaries here")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(summaries) { summary in
                        SummaryRowView(summary: summary)
                    }
                }
            }
            .navigationTitle("Recent Summaries")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Refresh") {
                        loadSummaries()
                    }
                }
            }
        }
        .onAppear {
            loadSummaries()
        }
    }
    
    private func loadSummaries() {
        isLoading = true
        errorMessage = nil
        
        Task {
            let result = await networkManager.fetchRecentSummaries()
            
            await MainActor.run {
                isLoading = false
                
                switch result {
                case .success(let fetchedSummaries):
                    summaries = fetchedSummaries
                case .failure(let error):
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}

struct SummaryRowView: View {
    let summary: Summary
    @State private var isDownloading = false
    
    private let networkManager = NetworkManager.shared
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Summary #\(summary.id)")
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Spacer()
                
                Text(formatDate(summary.createdAt))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Text(summary.summary)
                .font(.body)
                .lineLimit(3)
                .multilineTextAlignment(.leading)
            
            if let tag = summary.tag, !tag.isEmpty {
                Text("Tag: \(tag)")
                    .font(.caption)
                    .foregroundColor(.blue)
                    .italic()
            }
            
            HStack {
                Button(action: {
                    downloadTranscription()
                }) {
                    HStack(spacing: 4) {
                        if isDownloading {
                            ProgressView()
                                .scaleEffect(0.7)
                        } else {
                            Image(systemName: "square.and.arrow.down")
                        }
                        Text("Download Transcript")
                    }
                }
                .disabled(isDownloading)
                .buttonStyle(.bordered)
                
                Spacer()
                
                Button("Copy Summary") {
                    let pasteboard = NSPasteboard.general
                    pasteboard.clearContents()
                    pasteboard.setString(summary.summary, forType: .string)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(.vertical, 8)
    }
    
    private func downloadTranscription() {
        isDownloading = true
        
        Task {
            let result = await networkManager.downloadTranscription(summaryId: summary.id)
            
            await MainActor.run {
                isDownloading = false
                
                switch result {
                case .success(let transcription):
                    saveTranscription(transcription)
                case .failure(let error):
                    showErrorAlert(error.localizedDescription)
                }
            }
        }
    }
    
    private func saveTranscription(_ transcription: String) {
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = "meeting_transcript_\(summary.id).txt"
        savePanel.allowedContentTypes = [.plainText]
        
        if savePanel.runModal() == .OK {
            guard let url = savePanel.url else { return }
            
            do {
                try transcription.write(to: url, atomically: true, encoding: .utf8)
                
                // Show success notification
                let content = UNMutableNotificationContent()
                content.title = "Transcript Downloaded"
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
}

struct SummariesView_Previews: PreviewProvider {
    static var previews: some View {
        SummariesView()
    }
} 