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
    /// Imported documents waiting for LibraryView to insert them into the model context.
    var pending: [Document] = []

    func importFile(at url: URL) async {
        isImporting = true
        defer { isImporting = false }
        let secured = url.startAccessingSecurityScopedResource()
        defer { if secured { url.stopAccessingSecurityScopedResource() } }

        do {
            let type = UTType(filenameExtension: url.pathExtension) ?? .data
            let title = url.deletingPathExtension().lastPathComponent
            if type.conforms(to: .pdf) {
                pending.append(try importPDF(url: url, title: title))
            } else if type.conforms(to: .epub) {
                pending.append(try EPUBImporter.document(from: url, title: title))
            } else if type.conforms(to: .plainText) {
                let text = try String(contentsOf: url, encoding: .utf8)
                pending.append(Document(title: title, kind: .text, sentences: TextCleaner.sentences(fromPlainText: text), sourceURL: url))
            } else {
                throw ImportError.unsupported(url.pathExtension)
            }
        } catch {
            lastError = error.localizedDescription
        }
    }

    func importText(_ text: String, title: String = "Pasted text") {
        pending.append(Document(title: title, kind: .text, sentences: TextCleaner.sentences(fromPlainText: text)))
    }

    func importArticle(from url: URL) async {
        isImporting = true
        defer { isImporting = false }
        do {
            pending.append(try await ArticleImporter.document(from: url))
        } catch {
            lastError = error.localizedDescription
        }
    }

    /// Handles `narrata://inbox` from the share extension and any file left in the
    /// App Group inbox by it.
    func handle(url: URL) async {
        if url.scheme == "narrata" {
            if url.host() == "inbox" { await drainInbox() }
            return
        }
        await importFile(at: url)
    }

    static let appGroupID = "group.com.theoryofweb.narrata"

    func drainInbox() async {
        guard let inbox = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: Self.appGroupID)?
            .appending(path: "inbox", directoryHint: .isDirectory),
              let items = try? FileManager.default.contentsOfDirectory(at: inbox, includingPropertiesForKeys: nil) else { return }
        for item in items.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
            switch item.pathExtension {
            case "url":
                if let s = try? String(contentsOf: item, encoding: .utf8), let link = URL(string: s.trimmingCharacters(in: .whitespacesAndNewlines)) {
                    await importArticle(from: link)
                }
            case "txt":
                if let s = try? String(contentsOf: item, encoding: .utf8) { importText(s, title: "Shared text") }
            default:
                await importFile(at: item)
            }
            try? FileManager.default.removeItem(at: item)
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
