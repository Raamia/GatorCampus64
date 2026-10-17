import CryptoKit
import Foundation
import Security

public struct GameRun: Codable, Equatable, Sendable {
    public let runId: String
    public let missionId: String
    public let elapsedFrames: Int
    public let retries: Int
    public let assisted: Bool
    public let gameVersion: String

    public init(runId: String, missionId: String, elapsedFrames: Int, retries: Int, assisted: Bool, gameVersion: String) {
        self.runId = runId
        self.missionId = missionId
        self.elapsedFrames = elapsedFrames
        self.retries = retries
        self.assisted = assisted
        self.gameVersion = gameVersion
    }
}

public struct CachedLeaderboardRow: Equatable, Sendable {
    public let playerTag: String
    public let elapsedFrames: Int
    public let retries: Int

    public init(playerTag: String, elapsedFrames: Int, retries: Int) {
        self.playerTag = playerTag
        self.elapsedFrames = elapsedFrames
        self.retries = retries
    }
}

public enum BridgeError: Error, LocalizedError {
    case invalidRun(line: Int)
    case invalidCallback
    case invalidAppURL
    case invalidLeaderboardCache
    case processFailed(String)

    public var errorDescription: String? {
        switch self {
        case .invalidRun(let line): return "Outbox line \(line) has invalid fields. The file was left unchanged."
        case .invalidCallback: return "OAuth callback had a missing code or incorrect state."
        case .invalidAppURL: return "Use the deployed app origin, such as https://gator-field-board.app.space."
        case .invalidLeaderboardCache: return "The leaderboard response contained invalid data; the game cache was left unchanged."
        case .processFailed(let message): return message
        }
    }
}

private let runIdPattern = try! NSRegularExpression(pattern: "^[A-Za-z0-9_-]{8,80}$")
private let missionIdPattern = try! NSRegularExpression(pattern: "^[a-z0-9][a-z0-9_-]{1,79}$")
private let versionPattern = try! NSRegularExpression(pattern: "^[A-Za-z0-9._+-]{1,32}$")

private func matches(_ pattern: NSRegularExpression, _ value: String) -> Bool {
    let range = NSRange(value.startIndex..<value.endIndex, in: value)
    return pattern.firstMatch(in: value, range: range)?.range == range
}

/// Parse the six pipe-delimited fields emitted by mods/sgl64/sgl_deepspace.lua.
/// Strict parsing prevents malformed or hand-edited rows from being uploaded.
public func parseOutbox(_ text: String) throws -> [GameRun] {
    var result: [GameRun] = []
    for (index, rawLine) in text.split(whereSeparator: \.isNewline).enumerated() {
        let fields = rawLine.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
        guard fields.count == 6,
              matches(runIdPattern, fields[0]), matches(missionIdPattern, fields[1]),
              let frames = Int(fields[2]), (1...108_000).contains(frames),
              let retries = Int(fields[3]), (0...100).contains(retries),
              fields[4] == "0" || fields[4] == "1",
              matches(versionPattern, fields[5]) else {
            throw BridgeError.invalidRun(line: index + 1)
        }
        result.append(GameRun(runId: fields[0], missionId: fields[1], elapsedFrames: frames,
                              retries: retries, assisted: fields[4] == "1", gameVersion: fields[5]))
    }
    return result
}

/// Create safe `mod_storage` key/value updates consumed by the Lua game mod.
public func leaderboardStorageUpdates(
    missionID: String,
    rows: [CachedLeaderboardRow],
    updatedAt: Int64
) throws -> [String: String] {
    let playerTagPattern = try! NSRegularExpression(pattern: "^[A-Za-z0-9_-]{1,32}$")
    guard matches(missionIdPattern, missionID), rows.count <= 10, updatedAt > 0 else {
        throw BridgeError.invalidLeaderboardCache
    }
    let prefix = "sgl_ds_lb_\(missionID)_"
    var updates = [
        prefix + "count": String(rows.count),
        prefix + "updated": String(updatedAt),
    ]
    for (index, row) in rows.enumerated() {
        guard matches(playerTagPattern, row.playerTag),
              (1...108_000).contains(row.elapsedFrames), (0...100).contains(row.retries) else {
            throw BridgeError.invalidLeaderboardCache
        }
        updates[prefix + String(index + 1)] = "\(row.playerTag)|\(row.elapsedFrames)|\(row.retries)"
    }
    return updates
}

/// Merge leaderboard keys into the game's plain-text mod-storage save, removing stale rows
/// for the specified key prefixes while preserving unrelated settings and mod data.
public func mergeModStorage(_ text: String, updates: [String: String], clearingPrefixes: [String]) -> String {
    var lines = text.components(separatedBy: "\n")
    let hadFinalNewline = lines.last == ""
    if hadFinalNewline { lines.removeLast() }

    var storageHeader: Int?
    var storageEnd = lines.count
    for index in lines.indices {
        if lines[index] == "[storage]" {
            storageHeader = index
            if index + 1 < lines.count {
                storageEnd = ((index + 1)..<lines.count).first(where: { lines[$0].hasPrefix("[") }) ?? lines.count
            }
            break
        }
    }

    if storageHeader == nil {
        if !lines.isEmpty && !lines.last!.isEmpty { lines.append("") }
        lines.append("[storage]")
        storageHeader = lines.count - 1
        storageEnd = lines.count
    }

    guard let header = storageHeader else { return text }
    let valueStart = header + 1
    let originalStorage = Array(lines[valueStart..<storageEnd])
    let retained = originalStorage.filter { line in
        guard let equals = line.firstIndex(of: "=") else { return true }
        let key = String(line[..<equals])
        return !clearingPrefixes.contains { key.hasPrefix($0) }
    }
    let replacement = updates.keys.sorted().map { "\($0)=\(updates[$0]!)" }
    lines.replaceSubrange(valueStart..<storageEnd, with: retained + replacement)
    return lines.joined(separator: "\n") + (hadFinalNewline || !lines.isEmpty ? "\n" : "")
}

public func normalizedAppOrigin(_ value: String) throws -> URL {
    guard let components = URLComponents(string: value),
          let scheme = components.scheme?.lowercased(),
          let host = components.host, !host.isEmpty,
          components.user == nil, components.password == nil,
          components.query == nil, components.fragment == nil else { throw BridgeError.invalidAppURL }
    let isSecure = scheme == "https"
    let isLocalHttp = scheme == "http" && ["127.0.0.1", "localhost", "::1"].contains(host.lowercased())
    guard isSecure || isLocalHttp else { throw BridgeError.invalidAppURL }
    var normalized = components
    normalized.path = ""
    guard let url = normalized.url else { throw BridgeError.invalidAppURL }
    return url
}

public func base64URL(_ data: Data) -> String {
    data.base64EncodedString().replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
}

public func oauthStartURL(appOrigin: URL, redirectURI: String, state: String, verifier: String) -> URL? {
    let challenge = base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))
    var components = URLComponents(url: appOrigin.appending(path: "/api/auth/native-start"), resolvingAgainstBaseURL: false)
    components?.queryItems = [
        URLQueryItem(name: "provider", value: "google"),
        URLQueryItem(name: "redirect_uri", value: redirectURI),
        URLQueryItem(name: "state", value: state),
        URLQueryItem(name: "code_challenge", value: challenge),
        URLQueryItem(name: "code_challenge_method", value: "S256"),
    ]
    return components?.url
}

public func parseOAuthCallback(_ url: URL, expectedState: String) throws -> String {
    guard url.scheme == "http", url.host == "127.0.0.1", url.port == 45173,
          url.path == "/callback", let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
          components.queryItems?.first(where: { $0.name == "state" })?.value == expectedState,
          let code = components.queryItems?.first(where: { $0.name == "code" })?.value,
          (8...4096).contains(code.utf8.count) else { throw BridgeError.invalidCallback }
    return code
}

public func createVerifier() throws -> String {
    var bytes = [UInt8](repeating: 0, count: 32)
    guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
        throw BridgeError.processFailed("The system cryptographic random generator failed. Sign-in was stopped.")
    }
    return base64URL(Data(bytes))
}
