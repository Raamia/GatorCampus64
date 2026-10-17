import CryptoKit
import Foundation
import Testing
@testable import BridgeCore

@Test func parsesGameOutboxRowsAndAssistedFlag() throws {
    let runs = try parseOutbox("sgl_125_1|reitz_rooftop|900|2|0|0.1.0\nsgl_190_2|marston_climb|1200|0|1|0.1.0\n")
    #expect(runs.count == 2)
    #expect(runs[0].elapsedFrames == 900)
    #expect(!runs[0].assisted)
    #expect(runs[1].assisted)
}

@Test func rejectsMalformedOutboxInsteadOfSkippingIt() {
    #expect(throws: BridgeError.self) { try parseOutbox("sgl_1|bad|0|0|0|0.1.0") }
    #expect(throws: BridgeError.self) { try parseOutbox("sgl_12345678|badMission|100|0|0|0.1.0") }
}

@Test func oauthURLUsesS256AndExactLoopbackRedirect() throws {
    let origin = try normalizedAppOrigin("https://gator-field-board.app.space/")
    let verifier = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-._~"
    let url = try #require(oauthStartURL(appOrigin: origin, redirectURI: "http://127.0.0.1:45173/callback", state: "random-state", verifier: verifier))
    let components = try #require(URLComponents(url: url, resolvingAgainstBaseURL: false))
    let items = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })
    let expected = base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))
    #expect(items["code_challenge"] == expected)
    #expect(items["code_challenge_method"] == "S256")
    #expect(items["redirect_uri"] == "http://127.0.0.1:45173/callback")
}

@Test func callbackRequiresMatchingStateAndLoopbackAddress() throws {
    let callback = try #require(URL(string: "http://127.0.0.1:45173/callback?code=abcdefgh1234&state=right"))
    #expect(try parseOAuthCallback(callback, expectedState: "right") == "abcdefgh1234")
    #expect(throws: BridgeError.self) { try parseOAuthCallback(callback, expectedState: "wrong") }
    #expect(throws: BridgeError.self) {
        try parseOAuthCallback(URL(string: "http://localhost:45173/callback?code=abcdefgh1234&state=right")!, expectedState: "right")
    }
    #expect(throws: BridgeError.self) {
        try parseOAuthCallback(URL(string: "http://127.0.0.1:45174/callback?code=abcdefgh1234&state=right")!, expectedState: "right")
    }
}

@Test func appURLRejectsInsecureRemoteHostsAndCredentials() {
    #expect(throws: BridgeError.self) { try normalizedAppOrigin("file:///tmp") }
    #expect(throws: BridgeError.self) { try normalizedAppOrigin("https://user:pass@example.com") }
    #expect(throws: BridgeError.self) { try normalizedAppOrigin("http://example.com") }
}

@Test func oauthVerifierHasPkceCompatibleLength() throws {
    #expect((43...128).contains(try createVerifier().count))
}

@Test func leaderboardCacheUpdatesAreValidatedAndMergedIntoStorage() throws {
    let updates = try leaderboardStorageUpdates(
        missionID: "reitz_rooftop",
        rows: [CachedLeaderboardRow(playerTag: "GATOR-AB12CD34", elapsedFrames: 900, retries: 2)],
        updatedAt: 1_800_000_000
    )
    #expect(updates["sgl_ds_lb_reitz_rooftop_count"] == "1")
    #expect(updates["sgl_ds_lb_reitz_rooftop_1"] == "GATOR-AB12CD34|900|2")

    let original = "[storage]\nfriend=raami\nsgl_ds_run_sequence=4\nsgl_ds_lb_reitz_rooftop_1=STALE|1000|0\n[other]\nkeep=yes\n"
    let merged = mergeModStorage(original, updates: updates, clearingPrefixes: ["sgl_ds_lb_reitz_rooftop_"])
    #expect(merged.contains("friend=raami\n"))
    #expect(merged.contains("sgl_ds_run_sequence=4\n"))
    #expect(merged.contains("sgl_ds_lb_reitz_rooftop_1=GATOR-AB12CD34|900|2\n"))
    #expect(merged.contains("[other]\nkeep=yes\n"))
    #expect(!merged.contains("STALE"))
}

@Test func leaderboardCacheRejectsUnsafeRows() {
    #expect(throws: BridgeError.self) {
        try leaderboardStorageUpdates(missionID: "reitz_rooftop", rows: [
            CachedLeaderboardRow(playerTag: "bad|tag", elapsedFrames: 900, retries: 0)
        ], updatedAt: 1_800_000_000)
    }
}
