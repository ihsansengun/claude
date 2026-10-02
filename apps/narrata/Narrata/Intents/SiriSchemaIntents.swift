import AppIntents

/// Siri AI / App Schemas (WWDC26 session 240).
///
/// The Audio domain in the iOS 27 SDK is a music-service schema set (addToLibrary, addToPlaylist,
/// createStation, playAudio with queue/affinity entities, …). It does not fit a document reader,
/// so Narrata adopts the System domain instead: search-in-app and open. Playback control by
/// voice ("pause", "skip") comes from the Now Playing remote commands in PlayerEngine.

/// "Search Narrata for climate"
@AppIntent(schema: .system.searchInApp)
struct SearchLibraryIntent: AppIntent {
    static let title: LocalizedStringResource = "Search Library"
    static let openAppWhenRun = true

    @Parameter(title: "Search")
    var criteria: StringSearchCriteria

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .search(criteria.term)
        return .result()
    }
}

/// "Open my physics notes in Narrata"
@AppIntent(schema: .system.open)
struct OpenDocumentIntent: AppIntent {
    static let title: LocalizedStringResource = "Open Document"
    static let openAppWhenRun = true

    @Parameter(title: "Document")
    var target: DocumentEntity

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .play(id: target.id)
        return .result()
    }
}
