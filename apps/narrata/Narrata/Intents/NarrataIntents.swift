import AppIntents
import SwiftData

/// App Intents for Siri, Shortcuts and the widget.
/// Day 9: adopt the Audio App Schema domain (WWDC26 session 240) by annotating these with the
/// schema macros once the exact names are confirmed in the SDK, e.g.
///   @AssistantIntent(schema: .audio.play) / .pause / .skipForward
/// and add `.system.searchInApp` so "search Narrata for climate" works.

struct ContinueListeningIntent: AppIntent {
    static let title: LocalizedStringResource = "Continue Listening"
    static let description = IntentDescription("Resumes the document you listened to most recently.")
    static let openAppWhenRun = true

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .continueListening
        return .result()
    }
}

struct PlayDocumentIntent: AppIntent {
    static let title: LocalizedStringResource = "Play Document"
    static let openAppWhenRun = true

    @Parameter(title: "Document")
    var document: DocumentEntity

    @MainActor
    func perform() async throws -> some IntentResult {
        AppRouter.shared.pendingAction = .play(id: document.id)
        return .result()
    }
}

struct DocumentEntity: AppEntity {
    static let typeDisplayRepresentation = TypeDisplayRepresentation(name: "Document")
    static let defaultQuery = DocumentQuery()

    var id: UUID
    var title: String

    var displayRepresentation: DisplayRepresentation { DisplayRepresentation(title: "\(title)") }
}

struct DocumentQuery: EntityStringQuery {
    func entities(for identifiers: [UUID]) async throws -> [DocumentEntity] {
        try await fetch().filter { identifiers.contains($0.id) }
    }
    func entities(matching string: String) async throws -> [DocumentEntity] {
        try await fetch().filter { $0.title.localizedCaseInsensitiveContains(string) }
    }
    func suggestedEntities() async throws -> [DocumentEntity] {
        Array(try await fetch().prefix(5))
    }

    @MainActor
    private func fetch() throws -> [DocumentEntity] {
        let context = ModelContext(try ModelContainer(for: Document.self))
        var descriptor = FetchDescriptor<Document>(sortBy: [SortDescriptor(\.lastOpenedAt, order: .reverse)])
        descriptor.fetchLimit = 50
        return try context.fetch(descriptor).map { DocumentEntity(id: $0.id, title: $0.title) }
    }
}

struct NarrataShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ContinueListeningIntent(),
            phrases: ["Continue listening in \(.applicationName)", "Resume my document in \(.applicationName)"],
            shortTitle: "Continue Listening",
            systemImageName: "play.circle"
        )
    }
}

/// Bridges intents to the running UI.
@MainActor
@Observable
final class AppRouter {
    static let shared = AppRouter()
    enum Action { case continueListening, play(id: UUID) }
    var pendingAction: Action?
}
