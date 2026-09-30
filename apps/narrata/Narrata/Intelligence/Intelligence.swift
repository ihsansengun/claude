import Foundation

#if canImport(FoundationModels)
import FoundationModels
#endif

/// Apple Intelligence features with graceful fallbacks. Every call site must work when the
/// model is unavailable (older device, Apple Intelligence off, daily PCC limit reached).
///
/// API names below follow the WWDC26 sessions 241 and 319 as reported in third-party
/// write-ups; verify each against the iOS 27 SDK headers in Xcode 27 on day 7 and adjust.
enum Intelligence {
    enum Availability { case onDevice, cloud, unavailable }

    static var availability: Availability {
        #if canImport(FoundationModels)
        if case .available = SystemLanguageModel.default.availability { return .onDevice }
        #endif
        return .unavailable
    }

    /// Three bullets shown before the first listen.
    static func preview(of document: Document) async -> [String]? {
        await generate(
            instructions: "You write three short bullet points that tell a listener what a document covers. Plain language, no markdown.",
            prompt: "Document title: \(document.title)\n\n\(document.fullText.prefix(6000))"
        ).map { $0.split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty } }
    }

    /// Rewrites one paragraph at a simpler reading level, keeping meaning.
    static func simplify(_ paragraph: String) async -> String? {
        await generate(
            instructions: "Rewrite the text for a reader who finds long sentences hard. Short sentences, common words, same meaning, same language as the input. Return only the rewritten text.",
            prompt: paragraph
        )
    }

    /// Whole-document summary. Prefers the larger Private Cloud Compute model when it is
    /// available (32K context); falls back to a chunked on-device summary.
    static func summary(of document: Document) async -> String? {
        #if canImport(FoundationModels)
        // TODO(day 7): switch to PrivateCloudComputeLanguageModel when SDK confirms the type:
        //   let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel.default, instructions: ...)
        #endif
        let text = document.fullText
        if text.count <= 6000 {
            return await generate(instructions: summaryInstructions, prompt: text)
        }
        // Chunk → summarise each → summarise the summaries.
        var partials: [String] = []
        var index = text.startIndex
        while index < text.endIndex {
            let end = text.index(index, offsetBy: 6000, limitedBy: text.endIndex) ?? text.endIndex
            if let p = await generate(instructions: summaryInstructions, prompt: String(text[index..<end])) {
                partials.append(p)
            }
            index = end
        }
        guard !partials.isEmpty else { return nil }
        return await generate(instructions: summaryInstructions, prompt: partials.joined(separator: "\n\n"))
    }

    private static let summaryInstructions =
        "Summarise the document in one short paragraph followed by up to five key points. Plain language, no markdown, same language as the input."

    private static func generate(instructions: String, prompt: String) async -> String? {
        #if canImport(FoundationModels)
        guard availability != .unavailable else { return nil }
        do {
            let session = LanguageModelSession(instructions: instructions)
            let response = try await session.respond(to: prompt)
            return response.content
        } catch {
            return nil
        }
        #else
        return nil
        #endif
    }
}
