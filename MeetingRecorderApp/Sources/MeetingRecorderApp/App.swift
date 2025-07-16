import SwiftUI

// Main entry point for the macOS app
@main
struct MeetingRecorderApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        Settings {
            SettingsView()
                .environmentObject(AudioManager.shared)
                .environmentObject(NetworkManager.shared)
        }
    }
} 