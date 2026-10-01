import SwiftUI
import SwiftData

@main
struct NarrataApp: App {
    @State private var player = PlayerEngine()
    @State private var importer = DocumentImporter()
    @State private var store = Store()
    @AppStorage("hasOnboarded") private var hasOnboarded = false

    var body: some Scene {
        WindowGroup {
            Group {
                if hasOnboarded { LibraryView() } else { OnboardingView() }
            }
                .environment(player)
                .environment(importer)
                .environment(store)
                .task { await store.load() }
                .task { await importer.drainInbox() }
                .onOpenURL { url in
                    Task { await importer.handle(url: url) }
                }
        }
        .modelContainer(for: [Document.self], isAutosaveEnabled: true)
    }
}
