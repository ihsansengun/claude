import SwiftUI
import UIKit

struct ReadingPrefs: Codable, Equatable {
    var fontChoice: FontChoice = .system
    var fontSize: Double = 20
    var lineSpacing: Double = 8
    var letterSpacing: Double = 0
    var paragraphSpacing: Double = 18
    var theme: Theme = .paper
    var focusMode = false     // dims sentences other than the active one
    var followAlong = true    // auto-scroll

    enum FontChoice: String, Codable, CaseIterable { case system, rounded, serif, mono }
    enum Theme: String, Codable, CaseIterable { case paper, dark, sepia, highContrast, blueTint }

    /// The in-app size is a base; it still scales with the system Dynamic Type setting so
    /// "Larger Text" users get both controls.
    var font: Font {
        let size = UIFontMetrics(forTextStyle: .body).scaledValue(for: fontSize)
        switch fontChoice {
        case .system: return .system(size: size)
        case .rounded: return .system(size: size, design: .rounded)
        case .serif: return .system(size: size, design: .serif)
        case .mono: return .system(size: size, design: .monospaced)
        }
    }
}

/// All themes are chosen to pass WCAG AA (≥ 4.5:1) text contrast.
extension ReadingPrefs.Theme {
    var background: Color {
        switch self {
        case .paper: Color(red: 0.99, green: 0.98, blue: 0.96)
        case .dark: Color(red: 0.09, green: 0.09, blue: 0.10)
        case .sepia: Color(red: 0.96, green: 0.91, blue: 0.80)
        case .highContrast: .black
        case .blueTint: Color(red: 0.88, green: 0.93, blue: 0.98)
        }
    }
    var text: Color {
        switch self {
        case .paper, .sepia, .blueTint: Color(red: 0.12, green: 0.12, blue: 0.14)
        case .dark: Color(red: 0.90, green: 0.90, blue: 0.88)
        case .highContrast: .white
        }
    }
    var sentenceHighlight: Color {
        switch self {
        case .paper, .sepia, .blueTint: Color.yellow.opacity(0.35)
        case .dark: Color.yellow.opacity(0.25)
        case .highContrast: Color.yellow.opacity(0.45)
        }
    }
    var wordHighlight: Color {
        switch self {
        case .highContrast: .yellow
        default: Color.orange.opacity(0.55)
        }
    }
}

struct ReadingSettingsView: View {
    @Binding var prefs: ReadingPrefs
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Text") {
                    Picker("Font", selection: $prefs.fontChoice) {
                        ForEach(ReadingPrefs.FontChoice.allCases, id: \.self) { Text($0.rawValue.capitalized).tag($0) }
                    }
                    LabeledSlider("Size", value: $prefs.fontSize, range: 14...40)
                    LabeledSlider("Line spacing", value: $prefs.lineSpacing, range: 0...24)
                    LabeledSlider("Letter spacing", value: $prefs.letterSpacing, range: 0...4)
                }
                Section("Theme") {
                    Picker("Theme", selection: $prefs.theme) {
                        ForEach(ReadingPrefs.Theme.allCases, id: \.self) { Text(label(for: $0)).tag($0) }
                    }
                    .pickerStyle(.inline)
                }
                Section("Focus") {
                    Toggle("Dim other sentences", isOn: $prefs.focusMode)
                    Toggle("Scroll with the voice", isOn: $prefs.followAlong)
                }
                Section {
                    Button("Reset to defaults", role: .destructive) { prefs = ReadingPrefs() }
                }
            }
            .navigationTitle("Reading Settings")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }

    private func label(for theme: ReadingPrefs.Theme) -> String {
        switch theme {
        case .paper: "Paper"
        case .dark: "Dark"
        case .sepia: "Sepia"
        case .highContrast: "High contrast"
        case .blueTint: "Blue tint"
        }
    }
}

struct LabeledSlider: View {
    let label: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    init(_ label: String, value: Binding<Double>, range: ClosedRange<Double>) {
        self.label = label; _value = value; self.range = range
    }
    var body: some View {
        VStack(alignment: .leading) {
            Text(label)
            Slider(value: $value, in: range) { Text(label) }
                .accessibilityValue("\(Int(value))")
        }
    }
}
