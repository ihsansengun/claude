import Foundation

/// Fetches a web page and keeps the article body. A lightweight readability pass:
/// prefer <article>/<main>, else the largest text block.
enum ArticleImporter {
    static func document(from url: URL) async throws -> Document {
        let (data, _) = try await URLSession.shared.data(from: url)
        guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
            throw ImportError.network
        }
        let title = firstMatch(in: html, pattern: "<title[^>]*>([^<]+)</title>") ?? url.host() ?? "Article"
        let body = firstMatch(in: html, pattern: "<article[\\s\\S]*?</article>")
            ?? firstMatch(in: html, pattern: "<main[\\s\\S]*?</main>")
            ?? html
        let text = EPUBImporter.plainText(fromHTML: body)
        let sentences = TextCleaner.sentences(fromPlainText: text)
        guard sentences.count > 3 else { throw ImportError.unreadable }
        return Document(title: decode(title), kind: .article, sentences: sentences, sourceURL: url)
    }

    private static func firstMatch(in s: String, pattern: String) -> String? {
        guard let re = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive),
              let m = re.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)) else { return nil }
        let r = m.numberOfRanges > 1 ? m.range(at: 1) : m.range
        return Range(r, in: s).map { String(s[$0]) }
    }

    private static func decode(_ s: String) -> String {
        EPUBImporter.plainText(fromHTML: s).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
