import Cocoa
import SwiftUI
import Sparkle
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var menuBarManager: MenuBarManager!
    private var updaterController: SPUStandardUpdaterController!
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenuBar()
        setupAutoUpdater()
        requestNotificationPermission()
    }
    
    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        menuBarManager = MenuBarManager(statusItem: statusItem)
    }
    
    private func setupAutoUpdater() {
        updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
    }
    
    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            if let error = error {
                print("Notification permission error: \(error)")
            }
        }
    }
} 