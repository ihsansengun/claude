import Foundation

/// Minimal EPUB reader: unzip, read the spine order from the OPF, strip XHTML to text.
/// Uses Foundation's Archive support via `FileManager` + `Process`-free unzip through
/// `NSFileCoordinator` is not available on iOS, so we rely on the ZIPFoundation package.
/// TODO(day 3): add ZIPFoundation via SPM in project.yml (`packages:`) and replace the stub.
enum EPUBImporter {
    static func document(from url: URL, title: String) throws -> Document {
        // Stub until ZIPFoundation is wired: fail loudly instead of importing garbage.
        throw ImportError.unsupported("epub (coming day 3)")
    }

    /// Shared with ArticleImporter: turn (X)HTML into paragraph-separated text.
    static func plainText(fromHTML html: String) -> String {
        var s = html
        // Drop scripts/styles entirely.
        for tag in ["script", "style", "nav", "header", "footer"] {
            s = s.replacingOccurrences(of: "<\(tag)[^>]*>[\\s\\S]*?</\(tag)>", with: "", options: .regularExpression)
        }
        // Block elements become paragraph breaks.
        s = s.replacingOccurrences(of: "</(p|div|h[1-6]|li|br|section|article)>", with: "\n\n", options: [.regularExpression, .caseInsensitive])
        s = s.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        s = decodeEntities(s)
        return s.replacingOccurrences(of: "\n{3,}", with: "\n\n", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func decodeEntities(_ s: String) -> String {
        guard let data = s.data(using: .utf8),
              let attributed = try? NSAttributedString(
                data: data,
                options: [.documentType: NSAttributedString.DocumentType.html, .characterEncoding: String.Encoding.utf8.rawValue],
                documentAttributes: nil)
        else { return s }
        return attributed.string
    }
}
