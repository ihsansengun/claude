import Foundation

/// Fetches a web page and keeps the article body. A lightweight readability pass:
/// prefer <article>/<main>, else the largest text block.
enum ArticleImporter {
    static func document(from url: URL) async throws -> Document {
        let (data, _) = try await URLSession.shared.data(from: url)
        guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
            throw ImportError.network
        }
        let (title, text) = extract(html: html, fallbackTitle: url.host() ?? "Article")
        let sentences = TextCleaner.sentences(fromPlainText: text)
        guard sentences.count > 3 else { throw ImportError.unreadable }
        return Document(title: title, kind: .article, sentences: sentences, sourceURL: url)
    }

    /// Pure part of the import, so it can be unit-tested without a network.
    static func extract(html: String, fallbackTitle: String) -> (title: String, text: String) {
        let rawTitle = EPUBImporter.firstMatch(in: html, pattern: "<title[^>]*>([^<]+)</title>") ?? fallbackTitle
        let body = EPUBImporter.matches(in: html, pattern: "<article[\\s\\S]*?</article>").first
            ?? EPUBImporter.matches(in: html, pattern: "<main[\\s\\S]*?</main>").first
            ?? html
        return (decode(rawTitle), EPUBImporter.plainText(fromHTML: body))
    }


    private static func decode(_ s: String) -> String {
        EPUBImporter.plainText(fromHTML: s).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
