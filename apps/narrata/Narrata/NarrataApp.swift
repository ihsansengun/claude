import SwiftUI
import SwiftData

@main
struct NarrataApp: App {
    @State private var player = PlayerEngine()
    @State private var importer = DocumentImporter()

    var body: some Scene {
        WindowGroup {
            LibraryView()
                .environment(player)
                .environment(importer)
                .task { await importer.drainInbox() }
                .onOpenURL { url in
                    Task { await importer.handle(url: url) }
                }
        }
        .modelContainer(for: [Document.self], isAutosaveEnabled: true)
    }
}
