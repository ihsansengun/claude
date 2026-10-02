import AppIntents

/// Siri AI / App Schemas, Audio domain (WWDC26 session 240). `playAudio` is confirmed in the
/// iOS 27 SDK; the remaining audio schemas stay gated until the CI schema dump names them.

@AppIntent(schema: .audio.playAudio)
struct SiriPlayIntent: AppIntent {
    static let title: LocalizedStringResource = "Play"
    static let openAppWhenRun = true

    @Parameter(title: "Document")
    var target: DocumentEntity?

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = target.map { .play(id: $0.id) } ?? .continueListening
        return .result()
    }
}

#if NARRATA_AUDIO_SCHEMA

@AppIntent(schema: .audio.pause)
struct SiriPauseIntent: AppIntent {
    static let title: LocalizedStringResource = "Pause"

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .pause
        return .result()
    }
}

@AppIntent(schema: .audio.skipForward)
struct SiriSkipForwardIntent: AppIntent {
    static let title: LocalizedStringResource = "Skip Forward"

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .skip(1)
        return .result()
    }
}

@AppIntent(schema: .audio.skipBackward)
struct SiriSkipBackwardIntent: AppIntent {
    static let title: LocalizedStringResource = "Skip Back"

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .skip(-1)
        return .result()
    }
}

#endif

/// "Search Narrata for climate" — the one schema every app should adopt.
@AppIntent(schema: .system.search)
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
