// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MeetingRecorderApp",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "MeetingRecorderApp",
            targets: ["MeetingRecorderApp"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.5.0"),
        .package(url: "https://github.com/daltoniam/Starscream.git", from: "4.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "MeetingRecorderApp",
            dependencies: [
                "Sparkle",
                "Starscream"
            ]
        ),
    ]
) 