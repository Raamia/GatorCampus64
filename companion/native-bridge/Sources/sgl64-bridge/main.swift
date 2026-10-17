import AppKit
import BridgeCore
import Darwin
import Foundation
import Security

private let redirectURI = "http://127.0.0.1:45173/callback"
private let keychainServicePrefix = "org.swamphacks.sgl64-bridge.session."

private struct Config: Codable { var appURL: String }
private struct ActionEnvelope: Decodable {
    let success: Bool
    let error: String?
    let data: JSONValue?
}
private enum JSONValue: Decodable {
    case object([String: JSONValue]), array([JSONValue]), string(String), number(Double), bool(Bool), null
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else if let value = try? container.decode([String: JSONValue].self) { self = .object(value) }
        else { self = .array(try container.decode([JSONValue].self)) }
    }
}

private enum CLIError: Error, LocalizedError {
    case usage
    case keychain(OSStatus)
    case http(Int, String)
    case processFailed(String)
    case gameRunning
    case noModFS
    case ambiguousModFS([String])
    case unzip(String)
    case checkpoint

    var errorDescription: String? {
        switch self {
        case .usage: return usageText
        case .keychain(let status): return "macOS Keychain error (\(status))."
        case .http(let status, let text): return "DeepSpace returned HTTP \(status): \(text)"
        case .processFailed(let message): return message
        case .gameRunning: return "Close SM64CoopDX before syncing so the .modfs save is stable, then retry."
        case .noModFS: return "No ModFS containing pending_runs.txt was found. Pass --modfs /path/to/mod.modfs."
        case .ambiguousModFS(let files): return "Several ModFS archives contain the outbox; pass --modfs explicitly:\n" + files.joined(separator: "\n")
        case .unzip(let message): return message
        case .checkpoint: return "Could not save the local sync checkpoint. The server may already have accepted this run; retrying is safe."
        }
    }
}

private let usageText = """
SGL64 DeepSpace bridge

  sgl64-bridge login --app-url https://gator-field-board.app.space
  sgl64-bridge sync [--modfs /path/to/mod.modfs]
  sgl64-bridge leaderboard <mission-id>
  sgl64-bridge logout

Sign-in opens Google OAuth in the system browser and listens only on
http://127.0.0.1:45173/callback. The session token stays in macOS Keychain.
"""

private func supportDirectory() throws -> URL {
    let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
    let url = base.appending(path: "SGL64Bridge", directoryHint: .isDirectory)
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
}

private func configURL() throws -> URL { try supportDirectory().appending(path: "config.json") }
private func checkpointURL() throws -> URL { try supportDirectory().appending(path: "sync-checkpoints.json") }

private func readConfig() throws -> Config {
    let url = try configURL()
    guard let data = try? Data(contentsOf: url), let config = try? JSONDecoder().decode(Config.self, from: data) else {
        throw CLIError.usage
    }
    return config
}

private func saveConfig(_ config: Config) throws {
    let data = try JSONEncoder().encode(config)
    try data.write(to: configURL(), options: .atomic)
}

private func keychainService(appOrigin: URL) -> String { keychainServicePrefix + appOrigin.absoluteString }

private func saveSession(_ token: String, appOrigin: URL) throws {
    let service = keychainService(appOrigin: appOrigin)
    let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                kSecAttrService as String: service,
                                kSecAttrAccount as String: "sessionToken"]
    let data = Data(token.utf8)
    let update = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
    if update == errSecItemNotFound {
        var add = query
        add[kSecValueData as String] = data
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw CLIError.keychain(status) }
    } else if update != errSecSuccess { throw CLIError.keychain(update) }
}

private func loadSession(appOrigin: URL) throws -> String {
    let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                kSecAttrService as String: keychainService(appOrigin: appOrigin),
                                kSecAttrAccount as String: "sessionToken",
                                kSecReturnData as String: true,
                                kSecMatchLimit as String: kSecMatchLimitOne]
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data, let token = String(data: data, encoding: .utf8) else {
        throw CLIError.keychain(status)
    }
    return token
}

private func deleteSession(appOrigin: URL) throws {
    let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                kSecAttrService as String: keychainService(appOrigin: appOrigin),
                                kSecAttrAccount as String: "sessionToken"]
    let status = SecItemDelete(query as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else { throw CLIError.keychain(status) }
}

private func callbackCode(expectedState: String, ready: DispatchSemaphore, timeoutSeconds: Int = 240) throws -> String {
    let fd = socket(AF_INET, SOCK_STREAM, 0)
    guard fd >= 0 else { throw CLIError.processFailed("Could not create the local OAuth callback listener.") }
    defer { close(fd) }
    var reuse: Int32 = 1
    _ = setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, socklen_t(MemoryLayout<Int32>.size))
    var address = sockaddr_in()
    address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
    address.sin_family = sa_family_t(AF_INET)
    address.sin_port = in_port_t(45173).bigEndian
    address.sin_addr = in_addr(s_addr: in_addr_t(INADDR_LOOPBACK).bigEndian)
    let bound = withUnsafePointer(to: &address) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) }
    }
    guard bound == 0, listen(fd, 2) == 0 else {
        throw CLIError.processFailed("Could not listen on 127.0.0.1:45173. Close another app using that port and retry.")
    }
    ready.signal()
    print("Waiting for sign-in callback on \(redirectURI) …")
    let deadline = Date().addingTimeInterval(TimeInterval(timeoutSeconds))
    while Date() < deadline {
        var pollfd = pollfd(fd: fd, events: Int16(POLLIN), revents: 0)
        let remaining = max(1, Int(deadline.timeIntervalSinceNow * 1000))
        guard poll(&pollfd, 1, Int32(min(remaining, 1000))) >= 0 else { continue }
        if pollfd.revents & Int16(POLLIN) == 0 { continue }
        let client = accept(fd, nil, nil)
        guard client >= 0 else { continue }
        defer { close(client) }
        var bytes = [UInt8](repeating: 0, count: 16_384)
        let count = read(client, &bytes, bytes.count)
        guard count > 0, let request = String(bytes: bytes[..<count], encoding: .utf8),
              let firstLine = request.components(separatedBy: "\r\n").first,
              let target = firstLine.split(separator: " ").dropFirst().first,
              let callback = URL(string: "http://127.0.0.1:45173\(target)") else { continue }
        do {
            let code = try parseOAuthCallback(callback, expectedState: expectedState)
            let body = "Sign-in complete. You can return to SGL64 Bridge."
            let response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: \(body.utf8.count)\r\nConnection: close\r\n\r\n\(body)"
            _ = response.withCString { write(client, $0, response.utf8.count) }
            return code
        } catch {
            let body = "Invalid sign-in callback. Return to the terminal and retry login."
            let response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: \(body.utf8.count)\r\nConnection: close\r\n\r\n\(body)"
            _ = response.withCString { write(client, $0, response.utf8.count) }
        }
    }
    throw CLIError.processFailed("Sign-in timed out. Run login again.")
}

private func startLogin(appURL: String) async throws {
    let origin = try normalizedAppOrigin(appURL)
    let state = try createVerifier()
    let verifier = try createVerifier()
    guard let authURL = oauthStartURL(appOrigin: origin, redirectURI: redirectURI, state: state, verifier: verifier) else {
        throw BridgeError.invalidAppURL
    }
    // Start the listener before opening the browser so fast redirects are not lost.
    let ready = DispatchSemaphore(value: 0)
    let listener = Task.detached { try callbackCode(expectedState: state, ready: ready) }
    let readyStatus = await withCheckedContinuation { continuation in
        DispatchQueue.global().async {
            continuation.resume(returning: ready.wait(timeout: .now() + 5))
        }
    }
    guard readyStatus == .success else {
        listener.cancel()
        throw CLIError.processFailed("Could not start the local OAuth callback listener.")
    }
    let open = Process()
    open.executableURL = URL(fileURLWithPath: "/usr/bin/open")
    open.arguments = [authURL.absoluteString]
    try open.run()
    open.waitUntilExit()
    guard open.terminationStatus == 0 else { throw CLIError.processFailed("Could not open the system browser.") }
    let code = try await listener.value
    let exchange = try await postJSON(origin: origin, path: "/api/auth/native-exchange",
                                      body: ["code": code, "code_verifier": verifier])
    guard let session = exchange["sessionToken"] as? String else {
        throw CLIError.processFailed("DeepSpace did not return a session token.")
    }
    try saveSession(session, appOrigin: origin)
    try saveConfig(Config(appURL: origin.absoluteString))
    print("Signed in. The session is stored in macOS Keychain.")
}

private func request(_ url: URL, method: String = "GET", bearer: String? = nil, body: [String: Any]? = nil) async throws -> Data {
    var request = URLRequest(url: url)
    request.httpMethod = method
    request.timeoutInterval = 30
    if let bearer { request.setValue("Bearer \(bearer)", forHTTPHeaderField: "Authorization") }
    if let body {
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
    }
    let (data, response) = try await URLSession.shared.data(for: request)
    guard let http = response as? HTTPURLResponse else { throw CLIError.processFailed("DeepSpace returned an invalid HTTP response.") }
    guard (200..<300).contains(http.statusCode) else {
        let text = String(data: data, encoding: .utf8) ?? "Request failed"
        throw CLIError.http(http.statusCode, text)
    }
    return data
}

private func postJSON(origin: URL, path: String, body: [String: Any]) async throws -> [String: Any] {
    let data = try await request(origin.appending(path: path), method: "POST", body: body)
    return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
}

private func authenticatedContext() async throws -> (URL, String, String) {
    let config = try readConfig()
    let origin = try normalizedAppOrigin(config.appURL)
    let session = try loadSession(appOrigin: origin)
    let refreshed = try await postJSON(origin: origin, path: "/api/auth/native-token", body: ["sessionToken": session])
    guard let accessToken = refreshed["accessToken"] as? String else {
        throw CLIError.processFailed("DeepSpace did not return an access token. Run login again.")
    }
    let meData = try await request(origin.appending(path: "/api/auth/native-me"), bearer: accessToken)
    let me = try JSONSerialization.jsonObject(with: meData) as? [String: Any]
    guard let userId = me?["userId"] as? String else { throw CLIError.processFailed("Could not identify the signed-in account.") }
    return (origin, accessToken, userId)
}

private func gameIsRunning() -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
    process.arguments = ["-x", "sm64coopdx"]
    process.standardOutput = FileHandle.nullDevice
    process.standardError = FileHandle.nullDevice
    do { try process.run(); process.waitUntilExit(); return process.terminationStatus == 0 }
    catch { return false }
}

private func runUnzip(_ args: [String]) throws -> Data {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
    process.arguments = args
    let output = Pipe()
    process.standardOutput = output
    process.standardError = FileHandle.nullDevice
    try process.run()
    let data = output.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    guard process.terminationStatus == 0 else { throw CLIError.unzip("Could not read pending_runs.txt from this ModFS archive.") }
    return data
}

private func archiveContainsOutbox(_ url: URL) -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
    process.arguments = ["-Z1", url.path]
    let output = Pipe()
    process.standardOutput = output
    process.standardError = FileHandle.nullDevice
    do { try process.run() } catch { return false }
    let data = output.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    guard process.terminationStatus == 0, let listing = String(data: data, encoding: .utf8) else { return false }
    return listing.split(whereSeparator: \.isNewline).contains("pending_runs.txt")
}

private func findModFS(explicitPath: String?) throws -> (URL, String) {
    if let explicitPath {
        let url = URL(fileURLWithPath: explicitPath).standardizedFileURL
        guard archiveContainsOutbox(url) else { throw CLIError.unzip("The selected .modfs does not contain pending_runs.txt.") }
        return (url, String(data: try runUnzip(["-p", url.path, "pending_runs.txt"]), encoding: .utf8) ?? "")
    }
    let saveDir = FileManager.default.homeDirectoryForCurrentUser
        .appending(path: "Library/Application Support/sm64coopdx/sav", directoryHint: .isDirectory)
    let files = (try? FileManager.default.contentsOfDirectory(at: saveDir, includingPropertiesForKeys: nil)) ?? []
    let matches = files.filter { $0.pathExtension == "modfs" && archiveContainsOutbox($0) }
    guard !matches.isEmpty else { throw CLIError.noModFS }
    guard matches.count == 1, let archive = matches.first else { throw CLIError.ambiguousModFS(matches.map(\.path)) }
    return (archive, String(data: try runUnzip(["-p", archive.path, "pending_runs.txt"]), encoding: .utf8) ?? "")
}

private func readCheckpoints() throws -> [String: Set<String>] {
    let url = try checkpointURL()
    guard let data = try? Data(contentsOf: url) else { return [:] }
    let decoded = try JSONDecoder().decode([String: [String]].self, from: data)
    return decoded.mapValues(Set.init)
}

private func writeCheckpoints(_ values: [String: Set<String>]) throws {
    do {
        let normalized = values.mapValues { Array($0).sorted() }
        try JSONEncoder().encode(normalized).write(to: checkpointURL(), options: .atomic)
    } catch { throw CLIError.checkpoint }
}

private func action(origin: URL, accessToken: String, name: String, body: [String: Any]) async throws -> [String: Any] {
    let data = try await request(origin.appending(path: "/api/actions/\(name)"), method: "POST", bearer: accessToken, body: body)
    let envelope = try JSONDecoder().decode(ActionEnvelope.self, from: data)
    guard envelope.success else { throw CLIError.processFailed(envelope.error ?? "DeepSpace action failed.") }
    return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
}

private func sync(modfsPath: String?) async throws {
    guard !gameIsRunning() else { throw CLIError.gameRunning }
    let (origin, token, userId) = try await authenticatedContext()
    let (archive, text) = try findModFS(explicitPath: modfsPath)
    let runs = try parseOutbox(text)
    var checkpoints = try readCheckpoints()
    let checkpointKey = origin.absoluteString + ":" + userId
    var synced = checkpoints[checkpointKey, default: []]
    var submitted = 0
    for run in runs where !synced.contains(run.runId) {
        let result = try await action(origin: origin, accessToken: token, name: "submitGameRun", body: [
            "runId": run.runId, "missionId": run.missionId,
            "elapsedFrames": run.elapsedFrames, "retries": run.retries,
            "assisted": run.assisted, "gameVersion": run.gameVersion,
        ])
        guard (result["success"] as? Bool) == true else { throw CLIError.processFailed("Run \(run.runId) was rejected.") }
        synced.insert(run.runId)
        checkpoints[checkpointKey] = synced
        try writeCheckpoints(checkpoints)
        submitted += 1
    }
    print("Read \(runs.count) run(s) from \(archive.lastPathComponent); uploaded \(submitted), already synced \(runs.count - submitted).")
    print("The .modfs archive was not modified.")
}

private func showLeaderboard(missionId: String) async throws {
    let (origin, token, _) = try await authenticatedContext()
    let result = try await action(origin: origin, accessToken: token, name: "getGameLeaderboard",
                                  body: ["missionId": missionId, "limit": 10])
    guard let data = result["data"] as? [String: Any], let rows = data["rows"] as? [[String: Any]] else {
        throw CLIError.processFailed("Leaderboard response was missing rows.")
    }
    print("Leaderboard · \(missionId)")
    if rows.isEmpty { print("No unassisted runs yet."); return }
    for (index, row) in rows.enumerated() {
        let tag = row["playerTag"] as? String ?? "PLAYER"
        let frames = row["elapsedFrames"] as? Int ?? 0
        let retries = row["retries"] as? Int ?? 0
        let seconds = Double(frames) / 30.0
        print(String(format: "%2d  %@  %7.2fs  retries %d", index + 1, tag, seconds, retries))
    }
}

@main
private struct SGL64Bridge {
    static func main() async {
        do {
            let args = Array(CommandLine.arguments.dropFirst())
            guard let command = args.first else { throw CLIError.usage }
            switch command {
            case "login":
                guard let index = args.firstIndex(of: "--app-url"), args.indices.contains(index + 1) else { throw CLIError.usage }
                try await startLogin(appURL: args[index + 1])
            case "sync":
                var modfs: String?
                if let index = args.firstIndex(of: "--modfs") {
                    guard args.indices.contains(index + 1) else { throw CLIError.usage }
                    modfs = args[index + 1]
                }
                try await sync(modfsPath: modfs)
            case "leaderboard":
                guard args.count == 2 else { throw CLIError.usage }
                try await showLeaderboard(missionId: args[1])
            case "logout":
                let config = try readConfig()
                let origin = try normalizedAppOrigin(config.appURL)
                let session = try loadSession(appOrigin: origin)
                var revokeError: Error?
                do {
                    _ = try await postJSON(origin: origin, path: "/api/auth/native-signout", body: ["sessionToken": session])
                } catch {
                    revokeError = error
                }
                try deleteSession(appOrigin: origin)
                if let revokeError {
                    throw CLIError.processFailed("Removed the local Keychain session, but DeepSpace could not revoke it: \(revokeError.localizedDescription)")
                }
                print("Signed out and removed the local Keychain session.")
            case "help", "--help", "-h": print(usageText)
            default: throw CLIError.usage
            }
        } catch {
            fputs("Error: \(error.localizedDescription)\n", stderr)
            exit(1)
        }
    }
}
