import Foundation
import ZIPFoundation

/// EPUB 2/3 reader: unzip in memory, follow container.xml → OPF → spine order,
/// strip each XHTML chapter to text. Chapters become paragraph groups.
enum EPUBImporter {
    static func document(from url: URL, title fallbackTitle: String) throws -> Document {
        let archive = try Archive(url: url, accessMode: .read)

        guard let container = try archive.string(at: "META-INF/container.xml"),
              let opfPath = firstMatch(in: container, pattern: "full-path=\"([^\"]+)\"") else {
            throw ImportError.unreadable
        }
        guard let opf = try archive.string(at: opfPath) else { throw ImportError.unreadable }
        let opfDir = (opfPath as NSString).deletingLastPathComponent

        // manifest: id → href
        var hrefByID: [String: String] = [:]
        for item in matches(in: opf, pattern: "<item\\b[^>]*>") {
            if let id = firstMatch(in: item, pattern: "\\bid=\"([^\"]+)\""),
               let href = firstMatch(in: item, pattern: "\\bhref=\"([^\"]+)\"") {
                hrefByID[id] = href.removingPercentEncoding ?? href
            }
        }
        // spine: ordered idrefs
        let idrefs = matches(in: opf, pattern: "<itemref\\b[^>]*idref=\"([^\"]+)\"", group: 1)
        let title = firstMatch(in: opf, pattern: "<dc:title[^>]*>([^<]+)</dc:title>") ?? fallbackTitle

        var chapters: [String] = []
        for idref in idrefs {
            guard let href = hrefByID[idref] else { continue }
            let path = opfDir.isEmpty ? href : (opfDir as NSString).appendingPathComponent(href)
            if let html = try archive.string(at: path) {
                let body = firstMatch(in: html, pattern: "<body[^>]*>([\\s\\S]*)</body>") ?? html
                let text = plainText(fromHTML: body)
                if !text.isEmpty { chapters.append(text) }
            }
        }
        let sentences = TextCleaner.sentences(fromPlainText: chapters.joined(separator: "\n\n"))
        guard !sentences.isEmpty else { throw ImportError.unreadable }
        return Document(title: title.trimmingCharacters(in: .whitespacesAndNewlines), kind: .epub, sentences: sentences, sourceURL: url)
    }

    // MARK: - HTML → text (shared with ArticleImporter)

    static func plainText(fromHTML html: String) -> String {
        var s = html
        for tag in ["script", "style", "nav", "header", "footer", "aside"] {
            s = s.replacingOccurrences(of: "<\(tag)\\b[^>]*>[\\s\\S]*?</\(tag)>", with: "", options: [.regularExpression, .caseInsensitive])
        }
        s = s.replacingOccurrences(of: "<!--[\\s\\S]*?-->", with: "", options: .regularExpression)
        s = s.replacingOccurrences(of: "</(p|div|h[1-6]|li|section|article|blockquote|tr)>|<br\\s*/?>", with: "\n\n", options: [.regularExpression, .caseInsensitive])
        s = s.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        s = decodeEntities(s)
        s = s.replacingOccurrences(of: "[ \\t]+", with: " ", options: .regularExpression)
        s = s.replacingOccurrences(of: "\\s*\\n\\s*\\n\\s*", with: "\n\n", options: .regularExpression)
        return s.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Named and numeric entities without going through NSAttributedString (which is slow
    /// and main-thread-bound for HTML).
    private static func decodeEntities(_ s: String) -> String {
        var out = s
        let named: [String: String] = ["&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": "\"", "&apos;": "'", "&#39;": "'",
                                       "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–", "&hellip;": "…", "&rsquo;": "’",
                                       "&lsquo;": "‘", "&rdquo;": "”", "&ldquo;": "“", "&copy;": "©"]
        for (k, v) in named { out = out.replacingOccurrences(of: k, with: v) }
        for m in matches(in: out, pattern: "&#(x?[0-9A-Fa-f]+);") {
            let code = m.dropFirst(2).dropLast()
            let value = code.hasPrefix("x") ? UInt32(code.dropFirst(), radix: 16) : UInt32(code)
            if let value, let scalar = Unicode.Scalar(value) {
                out = out.replacingOccurrences(of: m, with: String(Character(scalar)))
            }
        }
        return out
    }

    // MARK: - Regex helpers

    static func firstMatch(in s: String, pattern: String) -> String? {
        matches(in: s, pattern: pattern, group: 1).first
    }

    static func matches(in s: String, pattern: String, group: Int = 0) -> [String] {
        guard let re = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else { return [] }
        return re.matches(in: s, range: NSRange(s.startIndex..., in: s)).compactMap { m in
            let r = m.numberOfRanges > group ? m.range(at: group) : m.range
            return Range(r, in: s).map { String(s[$0]) }
        }
    }
}

private extension Archive {
    func string(at path: String) throws -> String? {
        guard let entry = self[path] else { return nil }
        var data = Data()
        _ = try extract(entry) { data.append($0) }
        return String(data: data, encoding: .utf8)
    }
}
