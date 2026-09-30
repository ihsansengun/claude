import Foundation
import Vision
import UIKit

/// Photo of a page → sentences.
/// v1 uses the Vision text recognizer directly: it is deterministic and works offline on every
/// device. The Foundation Models `OCRTool` (iOS 27) is used in `Intelligence` for the "clean up
/// this scan" step, where a language model adds value (reflowing columns, dropping captions).
enum ScanImporter {
    static func document(from images: [UIImage], title: String = "Scanned pages") async throws -> Document {
        var pages: [String] = []
        for image in images {
            guard let cg = image.cgImage else { continue }
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true
            let handler = VNImageRequestHandler(cgImage: cg, orientation: .up)
            try handler.perform([request])
            let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
            pages.append(lines.joined(separator: "\n"))
        }
        let sentences = TextCleaner.sentences(from: pages)
        guard !sentences.isEmpty else { throw ImportError.unreadable }
        return Document(title: title, kind: .scan, sentences: sentences)
    }
}
