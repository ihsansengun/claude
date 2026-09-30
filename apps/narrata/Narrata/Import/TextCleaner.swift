import Foundation
import NaturalLanguage

/// Turns raw extracted text into clean sentences. This is where Listen AI is weak:
/// headers, footers, page numbers and broken hyphenation all end up spoken aloud.
enum TextCleaner {
    static func sentences(from pages: [String]) -> [Sentence] {
        let repeated = repeatedLines(in: pages)
        var paragraphs: [String] = []
        for page in pages {
            var lines = page.components(separatedBy: .newlines)
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty && !repeated.contains($0) && !isPageNumber($0) }
            lines = joinHyphenation(lines)
            paragraphs.append(contentsOf: mergeIntoParagraphs(lines))
        }
        return split(paragraphs: paragraphs)
    }

    static func sentences(fromPlainText text: String) -> [Sentence] {
        let paragraphs = text.components(separatedBy: "\n\n")
            .map { $0.replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        return split(paragraphs: paragraphs)
    }

    // MARK: - Heuristics

    /// Lines that appear on most pages are running headers/footers.
    private static func repeatedLines(in pages: [String]) -> Set<String> {
        guard pages.count >= 3 else { return [] }
        var counts: [String: Int] = [:]
        for page in pages {
            let lines = Set(page.components(separatedBy: .newlines).map { $0.trimmingCharacters(in: .whitespaces) })
            for l in lines where l.count > 3 { counts[l, default: 0] += 1 }
        }
        let threshold = max(3, pages.count / 2)
        return Set(counts.filter { $0.value >= threshold }.keys)
    }

    private static func isPageNumber(_ line: String) -> Bool {
        let stripped = line.replacingOccurrences(of: "Page", with: "", options: .caseInsensitive)
            .trimmingCharacters(in: .whitespaces)
        return stripped.count <= 5 && Int(stripped) != nil
    }

    /// "inter-\nnational" → "international"
    private static func joinHyphenation(_ lines: [String]) -> [String] {
        var out: [String] = []
        var carry = ""
        for line in lines {
            var l = carry + line
            carry = ""
            if l.hasSuffix("-"), let last = l.split(separator: " ").last, last.count > 2 {
                l.removeLast()
                carry = l
                continue
            }
            out.append(l)
        }
        if !carry.isEmpty { out.append(carry) }
        return out
    }

    /// A line ending without terminal punctuation continues the paragraph.
    private static func mergeIntoParagraphs(_ lines: [String]) -> [String] {
        var paragraphs: [String] = []
        var current = ""
        for line in lines {
            current += (current.isEmpty ? "" : " ") + line
            if let last = line.last, ".!?:\"”".contains(last) {
                paragraphs.append(current)
                current = ""
            }
        }
        if !current.isEmpty { paragraphs.append(current) }
        return paragraphs
    }

    private static func split(paragraphs: [String]) -> [Sentence] {
        var result: [Sentence] = []
        let tokenizer = NLTokenizer(unit: .sentence)
        for (pIndex, paragraph) in paragraphs.enumerated() {
            tokenizer.string = paragraph
            tokenizer.enumerateTokens(in: paragraph.startIndex..<paragraph.endIndex) { range, _ in
                let text = paragraph[range].trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty {
                    result.append(Sentence(id: result.count, paragraphIndex: pIndex, text: text))
                }
                return true
            }
        }
        return result
    }
}
