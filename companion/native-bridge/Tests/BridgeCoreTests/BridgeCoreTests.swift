import CryptoKit
import Foundation
import XCTest
@testable import BridgeCore

final class BridgeCoreTests: XCTestCase {
    func testParsesGameOutboxRowsAndAssistedFlag() throws {
        let runs = try parseOutbox("sgl_125_1|reitz_treasure|900|2|0|0.1.0\nsgl_190_2|marston_sprint|1200|0|1|0.1.0\n")
        XCTAssertEqual(runs.count, 2)
        XCTAssertEqual(runs[0].elapsedFrames, 900)
        XCTAssertFalse(runs[0].assisted)
        XCTAssertTrue(runs[1].assisted)
    }

    func testRejectsMalformedOutboxInsteadOfSkippingIt() {
        XCTAssertThrowsError(try parseOutbox("sgl_1|bad|0|0|0|0.1.0"))
        XCTAssertThrowsError(try parseOutbox("sgl_12345678|badMission|100|0|0|0.1.0"))
    }

    func testOAuthURLUsesS256AndExactLoopbackRedirect() throws {
        let origin = try normalizedAppOrigin("https://gator-field-board.app.space/")
        let verifier = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-._~"
        let url = try XCTUnwrap(oauthStartURL(appOrigin: origin, redirectURI: "http://127.0.0.1:45173/callback", state: "random-state", verifier: verifier))
        let components = try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false))
        let items = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })
        let expected = base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))
        XCTAssertEqual(items["code_challenge"], expected)
        XCTAssertEqual(items["code_challenge_method"], "S256")
        XCTAssertEqual(items["redirect_uri"], "http://127.0.0.1:45173/callback")
    }

    func testCallbackRequiresMatchingState() throws {
        let callback = try XCTUnwrap(URL(string: "http://127.0.0.1:45173/callback?code=abcdefgh1234&state=right"))
        XCTAssertEqual(try parseOAuthCallback(callback, expectedState: "right"), "abcdefgh1234")
        XCTAssertThrowsError(try parseOAuthCallback(callback, expectedState: "wrong"))
        XCTAssertThrowsError(try parseOAuthCallback(URL(string: "http://localhost:45173/callback?code=abcdefgh1234&state=right")!, expectedState: "right"))
        XCTAssertThrowsError(try parseOAuthCallback(URL(string: "http://127.0.0.1:45174/callback?code=abcdefgh1234&state=right")!, expectedState: "right"))
    }

    func testAppURLRejectsNonHTTPAndCredentials() {
        XCTAssertThrowsError(try normalizedAppOrigin("file:///tmp"))
        XCTAssertThrowsError(try normalizedAppOrigin("https://user:pass@example.com"))
        XCTAssertThrowsError(try normalizedAppOrigin("http://example.com"))
    }
}
