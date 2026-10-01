import SwiftUI

/// Three screens, no paywall, no account. Ends on the library with the Add menu highlighted.
struct OnboardingView: View {
    @AppStorage("hasOnboarded") private var hasOnboarded = false
    @State private var page = 0

    private let pages: [(icon: String, title: String, body: String)] = [
        ("headphones", "Listen to anything you'd read",
         "PDFs, books, articles and photos of pages become audio you can follow word by word."),
        ("textformat.size", "Reading that fits you",
         "Change the font, spacing and colours. Dim everything except the sentence being read. Works with VoiceOver, Voice Control and Dynamic Type."),
        ("lock.shield", "Private by design",
         "Your documents stay on your device. No account, no tracking, and the voices are free and work offline."),
    ]

    var body: some View {
        VStack {
            TabView(selection: $page) {
                ForEach(pages.indices, id: \.self) { i in
                    VStack(spacing: 24) {
                        Image(systemName: pages[i].icon)
                            .font(.system(size: 72))
                            .foregroundStyle(.tint)
                            .accessibilityHidden(true)
                        Text(pages[i].title).font(.title.bold()).multilineTextAlignment(.center)
                        Text(pages[i].body).font(.body).multilineTextAlignment(.center).foregroundStyle(.secondary)
                    }
                    .padding(32)
                    .tag(i)
                    .accessibilityElement(children: .combine)
                }
            }
            .tabViewStyle(.page)
            .indexViewStyle(.page(backgroundDisplayMode: .always))

            Button(page == pages.count - 1 ? "Start Listening" : "Continue") {
                if page == pages.count - 1 { hasOnboarded = true } else { page += 1 }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.bottom, 32)
        }
    }
}
