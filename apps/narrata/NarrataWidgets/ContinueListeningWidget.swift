import WidgetKit
import SwiftUI
import AppIntents

/// Small widget: title of the last document + progress; tapping resumes playback.
/// TODO(day 9): the timeline reads the last document from the App Group; this stub shows
/// placeholder data so the target compiles.
struct ContinueListeningWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "ContinueListening", provider: Provider()) { entry in
            VStack(alignment: .leading, spacing: 6) {
                Label("Continue", systemImage: "headphones").font(.caption).foregroundStyle(.secondary)
                Text(entry.title).font(.headline).lineLimit(2)
                ProgressView(value: entry.progress)
            }
            .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Continue Listening")
        .description("Pick up where you left off.")
        .supportedFamilies([.systemSmall])
    }
}

struct Entry: TimelineEntry { let date: Date; let title: String; let progress: Double }

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> Entry { Entry(date: .now, title: "Your last document", progress: 0.4) }
    func getSnapshot(in context: Context, completion: @escaping (Entry) -> Void) { completion(placeholder(in: context)) }
    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> Void) {
        completion(Timeline(entries: [placeholder(in: context)], policy: .never))
    }
}

@main
struct NarrataWidgetBundle: WidgetBundle {
    var body: some Widget { ContinueListeningWidget() }
}
