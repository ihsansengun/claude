import Foundation
import SwiftData

/// One item in the library. Text is stored as sentence-split paragraphs so the player
/// can highlight and skip without re-tokenising.
@Model
final class Document {
    enum Kind: String, Codable { case pdf, epub, article, text, scan }

    @Attribute(.unique) var id: UUID
    var title: String
    var kind: Kind
    var sourceURL: URL?
    var addedAt: Date
    var lastOpenedAt: Date?

    /// Flattened sentences; `paragraphIndex` lets the UI keep paragraph breaks.
    var sentences: [Sentence]
    /// Index of the sentence the listener stopped at.
    var progressSentence: Int
    var summary: String?

    init(title: String, kind: Kind, sentences: [Sentence], sourceURL: URL? = nil) {
        self.id = UUID()
        self.title = title
        self.kind = kind
        self.sentences = sentences
        self.sourceURL = sourceURL
        self.addedAt = .now
        self.progressSentence = 0
    }

    var fullText: String { sentences.map(\.text).joined(separator: " ") }
    var progressFraction: Double {
        sentences.isEmpty ? 0 : Double(progressSentence) / Double(sentences.count)
    }
    /// ~150 wpm at 1× speed.
    var estimatedMinutes: Int {
        let words = sentences.reduce(0) { $0 + $1.text.split(separator: " ").count }
        return max(1, words / 150)
    }
}

struct Sentence: Codable, Hashable, Identifiable {
    var id: Int
    var paragraphIndex: Int
    var text: String
}
