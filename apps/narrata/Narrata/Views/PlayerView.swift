import SwiftUI

struct PlayerView: View {
    let document: Document
    @Environment(PlayerEngine.self) private var player
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("readingPrefs") private var prefsData = Data()
    @State private var prefs = ReadingPrefs()
    @State private var showSettings = false
    @State private var preview: [String]?
    @State private var summary: String?

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: prefs.paragraphSpacing) {
                    if let preview { PreviewCard(bullets: preview) }
                    ForEach(paragraphs, id: \.0) { pIndex, sentences in
                        ParagraphView(sentences: sentences, prefs: prefs)
                            .id(pIndex)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 160)
            }
            .background(prefs.theme.background)
            .onChange(of: player.currentSentence) { _, idx in
                guard prefs.followAlong, idx < document.sentences.count else { return }
                let p = document.sentences[idx].paragraphIndex
                if reduceMotion { proxy.scrollTo(p, anchor: .center) }
                else { withAnimation { proxy.scrollTo(p, anchor: .center) } }
            }
        }
        .navigationTitle(document.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("Reading Settings", systemImage: "textformat.size") { showSettings = true }
            }
            ToolbarItem(placement: .secondaryAction) {
                Button("Summarize", systemImage: "text.badge.star") { Task { summary = await Intelligence.summary(of: document) } }
                    .disabled(Intelligence.availability == .unavailable)
            }
        }
        .safeAreaInset(edge: .bottom) { TransportBar() }
        .sheet(isPresented: $showSettings) { ReadingSettingsView(prefs: $prefs) }
        .sheet(item: $summary) { text in
            NavigationStack { ScrollView { Text(text).padding() }.navigationTitle("Summary") }
        }
        .task {
            prefs = (try? JSONDecoder().decode(ReadingPrefs.self, from: prefsData)) ?? ReadingPrefs()
            if document.progressSentence == 0 { preview = await Intelligence.preview(of: document) }
        }
        .onChange(of: prefs) { _, new in prefsData = (try? JSONEncoder().encode(new)) ?? Data() }
    }

    private var paragraphs: [(Int, [Sentence])] {
        Dictionary(grouping: document.sentences, by: \.paragraphIndex)
            .sorted { $0.key < $1.key }
            .map { ($0.key, $0.value) }
    }
}

extension String: @retroactive Identifiable { public var id: String { self } }

/// One paragraph; the active sentence and word are highlighted. Highlight uses an underline
/// in addition to colour so it survives "Differentiate Without Color".
struct ParagraphView: View {
    let sentences: [Sentence]
    let prefs: ReadingPrefs
    @Environment(PlayerEngine.self) private var player

    var body: some View {
        Text(attributed)
            .font(prefs.font)
            .lineSpacing(prefs.lineSpacing)
            .kerning(prefs.letterSpacing)
            .foregroundStyle(prefs.theme.text)
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(.rect)
            .onTapGesture { player.seek(toSentence: sentences.first?.id ?? 0) }
            .accessibilityAddTraits(.allowsDirectInteraction)
            .accessibilityAction(named: "Play from here") { player.seek(toSentence: sentences.first?.id ?? 0); player.play() }
    }

    private var attributed: AttributedString {
        var result = AttributedString()
        for s in sentences {
            var a = AttributedString(s.text + " ")
            let active = s.id == player.currentSentence
            if active {
                a.backgroundColor = prefs.theme.sentenceHighlight
                if let r = player.currentWordRange,
                   let lower = AttributedString.Index(r.lowerBound, within: a),
                   let upper = AttributedString.Index(r.upperBound, within: a) {
                    a[lower..<upper].backgroundColor = prefs.theme.wordHighlight
                    a[lower..<upper].underlineStyle = .single
                }
            } else if prefs.focusMode {
                a.foregroundColor = prefs.theme.text.opacity(0.35)
            }
            result += a
        }
        return result
    }
}

struct PreviewCard: View {
    let bullets: [String]
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("What this covers", systemImage: "sparkles").font(.headline)
            ForEach(bullets, id: \.self) { Text("• \($0)") }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial, in: .rect(cornerRadius: 12))
        .accessibilityElement(children: .combine)
    }
}

struct TransportBar: View {
    @Environment(PlayerEngine.self) private var player
    private let rates: [Float] = [0.75, 1, 1.25, 1.5, 2, 2.5, 3]

    var body: some View {
        @Bindable var player = player
        VStack(spacing: 8) {
            HStack(spacing: 28) {
                Button { player.skipParagraph(-1) } label: { Image(systemName: "backward.end.fill") }
                    .accessibilityLabel("Previous paragraph")
                Button { player.skipSentence(-1) } label: { Image(systemName: "gobackward") }
                    .accessibilityLabel("Previous sentence")
                Button(action: player.toggle) {
                    Image(systemName: player.isPlaying ? "pause.circle.fill" : "play.circle.fill").font(.system(size: 52))
                }
                .accessibilityLabel(player.isPlaying ? "Pause" : "Play")
                Button { player.skipSentence(1) } label: { Image(systemName: "goforward") }
                    .accessibilityLabel("Next sentence")
                Button { player.skipParagraph(1) } label: { Image(systemName: "forward.end.fill") }
                    .accessibilityLabel("Next paragraph")
            }
            .font(.title2)
            HStack {
                Menu {
                    ForEach(rates, id: \.self) { r in Button("\(r, specifier: "%.2g")×") { player.rate = r } }
                } label: { Text("\(player.rate, specifier: "%.2g")×").monospacedDigit() }
                .accessibilityLabel("Speed, \(player.rate, specifier: "%.2g") times")
                Spacer()
                Menu {
                    ForEach([15, 30, 45, 60], id: \.self) { m in Button("\(m) min") { player.sleepTimer = SleepTimer(minutes: m) } }
                    Button("Off") { player.sleepTimer = nil }
                } label: { Image(systemName: player.sleepTimer == nil ? "moon" : "moon.fill") }
                .accessibilityLabel("Sleep timer")
            }
            .font(.subheadline)
        }
        .padding()
        .glassEffect(in: .rect(cornerRadius: 20))
        .padding(.horizontal)
    }
}
