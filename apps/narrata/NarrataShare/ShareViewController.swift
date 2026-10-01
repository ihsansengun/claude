import UIKit
import UniformTypeIdentifiers

/// Share sheet target: receives a URL, text or file, drops it in the App Group inbox,
/// then opens the main app, which imports whatever is in the inbox on launch.
final class ShareViewController: UIViewController {
    static let groupID = "group.com.theoryofweb.narrata"

    override func viewDidLoad() {
        super.viewDidLoad()
        Task { await handle(); extensionContext?.completeRequest(returningItems: nil) }
    }

    private func handle() async {
        guard let inbox = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: Self.groupID)?
            .appending(path: "inbox", directoryHint: .isDirectory) else { return }
        try? FileManager.default.createDirectory(at: inbox, withIntermediateDirectories: true)

        for item in extensionContext?.inputItems as? [NSExtensionItem] ?? [] {
            for provider in item.attachments ?? [] {
                if provider.hasItemConformingToTypeIdentifier(UTType.url.identifier),
                   let url = try? await provider.loadItem(forTypeIdentifier: UTType.url.identifier) as? URL {
                    try? url.absoluteString.write(to: inbox.appending(path: "\(UUID().uuidString).url"), atomically: true, encoding: .utf8)
                } else if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier),
                          let text = try? await provider.loadItem(forTypeIdentifier: UTType.plainText.identifier) as? String {
                    try? text.write(to: inbox.appending(path: "\(UUID().uuidString).txt"), atomically: true, encoding: .utf8)
                } else if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier),
                          let src = try? await provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier) as? URL {
                    try? FileManager.default.copyItem(at: src, to: inbox.appending(path: src.lastPathComponent))
                }
            }
        }
        openContainerApp()
    }

    /// Share extensions can't call UIApplication.open directly; walking the responder chain
    /// to the hosting application is the long-standing workaround.
    private func openContainerApp() {
        guard let url = URL(string: "narrata://inbox") else { return }
        var responder: UIResponder? = self
        while let r = responder {
            if let app = r as? UIApplication {
                app.open(url, options: [:], completionHandler: nil)
                return
            }
            responder = r.next
        }
    }
}
