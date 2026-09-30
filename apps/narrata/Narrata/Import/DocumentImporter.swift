import Foundation
import PDFKit
import SwiftData
import UniformTypeIdentifiers
import Observation

/// Front door for every import path: Files, share sheet, URL, camera, paste.
@Observable
@MainActor
final class DocumentImporter {
    var isImporting = false
    var lastError: String?
    var pending: Document?   // set by importers; LibraryView inserts into the model context

    func importFile(at url: URL) async {
        isImporting = true
        defer { isImporting = false }
        let secured = url.startAccessingSecurityScopedResource()
        defer { if secured { url.stopAccessingSecurityScopedResource() } }

        do {
            let type = UTType(filenameExtension: url.pathExtension) ?? .data
            let title = url.deletingPathExtension().lastPathComponent
            if type.conforms(to: .pdf) {
                pending = try importPDF(url: url, title: title)
            } else if type.conforms(to: .epub) {
                pending = try EPUBImporter.document(from: url, title: title)
            } else if type.conforms(to: .plainText) {
                let text = try String(contentsOf: url, encoding: .utf8)
                pending = Document(title: title, kind: .text, sentences: TextCleaner.sentences(fromPlainText: text), sourceURL: url)
            } else {
                throw ImportError.unsupported(url.pathExtension)
            }
        } catch {
            lastError = error.localizedDescription
        }
    }

    func importText(_ text: String, title: String = "Pasted text") {
        pending = Document(title: title, kind: .text, sentences: TextCleaner.sentences(fromPlainText: text))
    }

    func importArticle(from url: URL) async {
        isImporting = true
        defer { isImporting = false }
        do {
            pending = try await ArticleImporter.document(from: url)
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func importPDF(url: URL, title: String) throws -> Document {
        guard let pdf = PDFDocument(url: url) else { throw ImportError.unreadable }
        var pages: [String] = []
        for i in 0..<pdf.pageCount {
            pages.append(pdf.page(at: i)?.string ?? "")
        }
        let docTitle = pdf.documentAttributes?[PDFDocumentAttribute.titleAttribute] as? String
        let sentences = TextCleaner.sentences(from: pages)
        guard !sentences.isEmpty else { throw ImportError.scannedPDF }
        return Document(title: docTitle?.isEmpty == false ? docTitle! : title, kind: .pdf, sentences: sentences, sourceURL: url)
    }
}

enum ImportError: LocalizedError {
    case unsupported(String), unreadable, scannedPDF, network

    var errorDescription: String? {
        switch self {
        case .unsupported(let ext): "“.\(ext)” files aren't supported yet."
        case .unreadable: "That file couldn't be opened."
        case .scannedPDF: "This PDF has no text layer. Use Scan to read it with the camera."
        case .network: "Couldn't load that page."
        }
    }
}
