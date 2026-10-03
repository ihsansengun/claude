import SwiftUI
import AVFoundation
import StoreKit

struct SettingsView: View {
    @Environment(PlayerEngine.self) private var player
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var purchaseError: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Voice") {
                    NavigationLink {
                        VoicePickerView()
                    } label: {
                        LabeledContent("Voice", value: player.voice?.name ?? "Default")
                    }
                    Text("More natural voices: Settings › Accessibility › Spoken Content › Voices, then download an Enhanced or Premium voice. They're free and work offline.")
                        .font(.footnote).foregroundStyle(.secondary)
                }

                Section("Narrata Plus") {
                    if store.hasPlus {
                        Label("Plus is active", systemImage: "checkmark.seal.fill").foregroundStyle(.green)
                        UsageMeter(used: store.cloudCharactersUsed, allowance: store.cloudCharacterAllowance)
                    } else {
                        Text("Cloud voices and unlimited summaries. Everything else in Narrata stays free, including every accessibility feature.")
                            .font(.footnote).foregroundStyle(.secondary)
                        ForEach(store.products, id: \.id) { product in
                            Button {
                                Task {
                                    do { try await store.purchase(product) } catch { purchaseError = error.localizedDescription }
                                }
                            } label: {
                                LabeledContent(product.displayName, value: product.displayPrice)
                            }
                        }
                        Button("Restore Purchases") { Task { await store.refreshEntitlements() } }
                    }
                }

                Section("About") {
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "")
                    Link("Privacy: nothing leaves your device", destination: URL(string: "https://theoryofweb.com/narrata/privacy")!)
                }
            }
            .navigationTitle("Settings")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .alert("Purchase failed", isPresented: .constant(purchaseError != nil)) {
                Button("OK") { purchaseError = nil }
            } message: { Text(purchaseError ?? "") }
        }
    }
}

/// The meter Listen AI doesn't show. Always visible to Plus users.
struct UsageMeter: View {
    let used: Int
    let allowance: Int
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ProgressView(value: Double(used), total: Double(allowance))
            Text("\(hours(used)) of \(hours(allowance)) hours of cloud voice used this period")
                .font(.footnote).foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
    }
    private func hours(_ chars: Int) -> String { String(format: "%.1f", Double(chars) / 54_000) }
}

struct VoicePickerView: View {
    @Environment(PlayerEngine.self) private var player
    private let voices = VoiceCatalog.all()
    /// Kept alive for the sample utterance; a temporary synthesizer is deallocated before it speaks.
    @State private var sampler = AVSpeechSynthesizer()

    var body: some View {
        List {
            ForEach(groupedLanguages, id: \.self) { language in
                Section(Locale.current.localizedString(forIdentifier: language) ?? language) {
                    ForEach(voices.filter { $0.language == language }, id: \.identifier) { voice in
                        Button {
                            player.voice = voice
                            sampler.stopSpeaking(at: .immediate)
                            sampler.speak(sample(for: voice))
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(voice.name)
                                    Text(qualityLabel(voice.quality)).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                if voice.identifier == player.voice?.identifier {
                                    Image(systemName: "checkmark").accessibilityLabel("Selected")
                                }
                            }
                        }
                        .tint(.primary)
                    }
                }
            }
        }
        .navigationTitle("Voices")
    }

    private var groupedLanguages: [String] {
        let current = Locale.preferredLanguages.first.map { String($0.prefix(2)) } ?? "en"
        let langs = Array(Set(voices.map(\.language))).sorted()
        return langs.filter { $0.hasPrefix(current) } + langs.filter { !$0.hasPrefix(current) }
    }

    private func sample(for voice: AVSpeechSynthesisVoice) -> AVSpeechUtterance {
        let u = AVSpeechUtterance(string: "This is how I sound reading your documents.")
        u.voice = voice
        return u
    }

    private func qualityLabel(_ q: AVSpeechSynthesisVoiceQuality) -> String {
        switch q {
        case .premium: "Premium"
        case .enhanced: "Enhanced"
        default: "Standard"
        }
    }
}
