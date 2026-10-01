import Foundation

/// Fetches a web page and keeps the article body. A lightweight readability pass:
/// prefer <article>/<main>, else the largest text block.
enum ArticleImporter {
    static func document(from url: URL) async throws -> Document {
        let (data, _) = try await URLSession.shared.data(from: url)
        guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
            throw ImportError.network
        }
        let title = EPUBImporter.firstMatch(in: html, pattern: "<title[^>]*>([^<]+)</title>") ?? url.host() ?? "Article"
        let body = EPUBImporter.matches(in: html, pattern: "<article[\\s\\S]*?</article>").first
            ?? EPUBImporter.matches(in: html, pattern: "<main[\\s\\S]*?</main>").first
            ?? html
        let text = EPUBImporter.plainText(fromHTML: body)
        let sentences = TextCleaner.sentences(fromPlainText: text)
        guard sentences.count > 3 else { throw ImportError.unreadable }
        return Document(title: decode(title), kind: .article, sentences: sentences, sourceURL: url)
    }


    private static func decode(_ s: String) -> String {
        EPUBImporter.plainText(fromHTML: s).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
