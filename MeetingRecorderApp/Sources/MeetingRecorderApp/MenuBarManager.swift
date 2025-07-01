import Cocoa
import SwiftUI
import UserNotifications

class MenuBarManager: ObservableObject {
    private let statusItem: NSStatusItem
    private let audioManager = AudioManager.shared
    private let networkManager = NetworkManager.shared
    
    @Published var isRecording = false
    @Published var isProcessing = false
    @Published var lastSummary: String?
    
    init(statusItem: NSStatusItem) {
        self.statusItem = statusItem
        setupStatusItem()
        setupMenu()
        observeAudioManager()
    }
    
    private func setupStatusItem() {
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Meeting Recorder")
            button.image?.isTemplate = true
            updateIcon()
        }
    }
    
    private func setupMenu() {
        let menu = NSMenu()
        
        // Recording controls
        let recordMenuItem = NSMenuItem(
            title: "🔴 Start Recording",
            action: #selector(toggleRecording),
            keyEquivalent: "r"
        )
        recordMenuItem.target = self
        menu.addItem(recordMenuItem)
        
        let stopMenuItem = NSMenuItem(
            title: "⏹️ Stop Recording",
            action: #selector(stopRecording),
            keyEquivalent: "s"
        )
        stopMenuItem.target = self
        stopMenuItem.isEnabled = false
        menu.addItem(stopMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Status and progress
        let statusMenuItem = NSMenuItem(title: "Status: Ready", action: nil, keyEquivalent: "")
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Recent summaries
        let summariesMenuItem = NSMenuItem(title: "📋 Recent Summaries", action: #selector(showSummaries), keyEquivalent: "")
        summariesMenuItem.target = self
        menu.addItem(summariesMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Settings
        let settingsMenuItem = NSMenuItem(title: "⚙️ Settings", action: #selector(showSettings), keyEquivalent: ",")
        settingsMenuItem.target = self
        menu.addItem(settingsMenuItem)
        
        // Check for updates
        let updateMenuItem = NSMenuItem(title: "🔄 Check for Updates", action: #selector(checkForUpdates), keyEquivalent: "")
        updateMenuItem.target = self
        menu.addItem(updateMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Quit
        let quitMenuItem = NSMenuItem(title: "❌ Quit Meeting Recorder", action: #selector(quit), keyEquivalent: "q")
        quitMenuItem.target = self
        menu.addItem(quitMenuItem)
        
        statusItem.menu = menu
    }
    
    private func observeAudioManager() {
        audioManager.onRecordingStateChanged = { [weak self] isRecording in
            DispatchQueue.main.async {
                self?.isRecording = isRecording
                self?.updateMenuItems()
                self?.updateIcon()
            }
        }
        
        audioManager.onProcessingStateChanged = { [weak self] isProcessing in
            DispatchQueue.main.async {
                self?.isProcessing = isProcessing
                self?.updateMenuItems()
                self?.updateIcon()
            }
        }
        
        audioManager.onSummaryReceived = { [weak self] summary in
            DispatchQueue.main.async {
                self?.lastSummary = summary
                self?.showSummaryNotification(summary)
                self?.updateMenuItems()
            }
        }
    }
    
    private func updateIcon() {
        guard let button = statusItem.button else { return }
        
        if isRecording {
            button.image = NSImage(systemSymbolName: "mic.fill", accessibilityDescription: "Recording")
            button.image?.isTemplate = false
            // Add red tint for recording
            let image = button.image?.copy() as? NSImage
            image?.lockFocus()
            NSColor.systemRed.set()
            NSRect(origin: .zero, size: image?.size ?? .zero).fill(using: .sourceAtop)
            image?.unlockFocus()
            button.image = image
        } else if isProcessing {
            button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "Processing")
            button.image?.isTemplate = true
        } else {
            button.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Ready")
            button.image?.isTemplate = true
        }
    }
    
    private func updateMenuItems() {
        guard let menu = statusItem.menu else { return }
        
        // Update recording menu items
        if let recordItem = menu.item(withTitle: "🔴 Start Recording") {
            recordItem.isEnabled = !isRecording && !isProcessing
        }
        
        if let stopItem = menu.item(withTitle: "⏹️ Stop Recording") {
            stopItem.isEnabled = isRecording
        }
        
        // Update status
        if let statusItem = menu.items.first(where: { $0.title.hasPrefix("Status:") }) {
            if isRecording {
                statusItem.title = "Status: 🔴 Recording..."
            } else if isProcessing {
                statusItem.title = "Status: ⚙️ Processing..."
            } else {
                statusItem.title = "Status: ✅ Ready"
            }
        }
    }
    
    private func showSummaryNotification(_ summary: String) {
        let content = UNMutableNotificationContent()
        content.title = "Meeting Summary Ready"
        content.body = String(summary.prefix(100)) + (summary.count > 100 ? "..." : "")
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Failed to show notification: \(error)")
            }
        }
    }
    
    // MARK: - Menu Actions
    
    @objc private func toggleRecording() {
        if isRecording {
            stopRecording()
        } else {
            startRecording()
        }
    }
    
    @objc private func startRecording() {
        audioManager.startRecording()
    }
    
    @objc private func stopRecording() {
        audioManager.stopRecording()
    }
    
    @objc private func showSummaries() {
        // Open a window showing recent summaries
        let summariesWindow = SummariesWindow()
        summariesWindow.showWindow(nil)
    }
    
    @objc private func showSettings() {
        // Open settings window
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }
    
    @objc private func checkForUpdates() {
        // Trigger Sparkle update check
        if NSApp.delegate is AppDelegate {
            // This would call the updater
            print("Checking for updates...")
        }
    }
    
    @objc private func quit() {
        NSApp.terminate(self)
    }
} 