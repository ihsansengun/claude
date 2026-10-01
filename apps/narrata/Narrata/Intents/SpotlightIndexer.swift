import CoreSpotlight
import UniformTypeIdentifiers
import Foundation

/// Donates library items to Core Spotlight so they show up in system search and Siri
/// (`system.searchInApp`), and later in a Foundation Models `SpotlightSearchTool`.
enum SpotlightIndexer {
    static let domain = "com.theoryofweb.narrata.documents"

    static func index(_ document: Document) {
        let attrs = CSSearchableItemAttributeSet(contentType: .text)
        attrs.title = document.title
        attrs.contentDescription = String(document.fullText.prefix(300))
        attrs.keywords = ["Narrata", "listen", document.kind.rawValue]
        let item = CSSearchableItem(uniqueIdentifier: document.id.uuidString, domainIdentifier: domain, attributeSet: attrs)
        CSSearchableIndex.default().indexSearchableItems([item])
    }

    static func remove(_ id: UUID) {
        CSSearchableIndex.default().deleteSearchableItems(withIdentifiers: [id.uuidString])
    }
}

/// Last-played snapshot shared with the widget through the App Group.
struct NowPlayingSnapshot: Codable {
    var id: UUID
    var title: String
    var progress: Double
    var updatedAt: Date

    static let fileName = "now-playing.json"

    static var url: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.theoryofweb.narrata")?
            .appending(path: fileName)
    }

    static func write(_ document: Document) {
        guard let url else { return }
        let snap = NowPlayingSnapshot(id: document.id, title: document.title, progress: document.progressFraction, updatedAt: .now)
        try? JSONEncoder().encode(snap).write(to: url, options: .atomic)
    }

    static func read() -> NowPlayingSnapshot? {
        guard let url, let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(NowPlayingSnapshot.self, from: data)
    }
}
