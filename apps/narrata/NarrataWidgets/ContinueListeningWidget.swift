import WidgetKit
import SwiftUI
import AppIntents

/// Small widget: title of the last document + progress; tapping resumes playback.
/// Reads the snapshot the app writes to the App Group on every progress save.
struct ContinueListeningWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "ContinueListening", provider: Provider()) { entry in
            VStack(alignment: .leading, spacing: 6) {
                Label("Continue", systemImage: "headphones").font(.caption).foregroundStyle(.secondary)
                Text(entry.title).font(.headline).lineLimit(2)
                ProgressView(value: entry.progress)
            }
            .containerBackground(.fill.tertiary, for: .widget)
            .widgetURL(URL(string: "narrata://continue"))
        }
        .configurationDisplayName("Continue Listening")
        .description("Pick up where you left off.")
        .supportedFamilies([.systemSmall])
    }
}

struct Entry: TimelineEntry { let date: Date; let title: String; let progress: Double }

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> Entry { Entry(date: .now, title: "Your last document", progress: 0.4) }
    func getSnapshot(in context: Context, completion: @escaping (Entry) -> Void) { completion(current()) }
    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> Void) {
        completion(Timeline(entries: [current()], policy: .never))
    }
    private func current() -> Entry {
        if let snap = SharedSnapshot.read() {
            return Entry(date: .now, title: snap.title, progress: snap.progress)
        }
        return Entry(date: .now, title: "Add something to listen to", progress: 0)
    }
}

/// Mirror of NowPlayingSnapshot in the app target (extensions don't share source by default).
private struct SharedSnapshot: Codable {
    var id: UUID; var title: String; var progress: Double; var updatedAt: Date
    static func read() -> SharedSnapshot? {
        guard let url = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.theoryofweb.narrata")?
                .appending(path: "now-playing.json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(SharedSnapshot.self, from: data)
    }
}

@main
struct NarrataWidgetBundle: WidgetBundle {
    var body: some Widget { ContinueListeningWidget() }
}
