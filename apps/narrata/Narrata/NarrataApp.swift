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
                .onOpenURL { url in
                    Task { await importer.importFile(at: url) }
                }
        }
        .modelContainer(for: [Document.self], isAutosaveEnabled: true)
    }
}
