import Cocoa
import SwiftUI
// import Sparkle // Temporarily disabled
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var menuBarManager: MenuBarManager!
    // private var updaterController: SPUStandardUpdaterController! // Temporarily disabled
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenuBar()
        // setupAutoUpdater() // Temporarily disabled
        requestNotificationPermission()
    }
    
    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        menuBarManager = MenuBarManager(statusItem: statusItem)
    }
    
    // Temporarily disabled auto-updater
    /*
    private func setupAutoUpdater() {
        updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
    }
    */
    
    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            if let error = error {
                print("Notification permission error: \(error)")
            }
        }
    }
} 