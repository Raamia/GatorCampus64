// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SGL64Bridge",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "BridgeCore", targets: ["BridgeCore"]),
        .executable(name: "sgl64-bridge", targets: ["sgl64-bridge"]),
    ],
    targets: [
        .target(name: "BridgeCore"),
        .executableTarget(name: "sgl64-bridge", dependencies: ["BridgeCore"]),
        .testTarget(name: "BridgeCoreTests", dependencies: ["BridgeCore"]),
    ]
)
