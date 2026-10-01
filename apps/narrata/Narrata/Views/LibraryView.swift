import SwiftUI
import SwiftData
import UniformTypeIdentifiers

struct LibraryView: View {
    @Environment(\.modelContext) private var context
    @Environment(PlayerEngine.self) private var player
    @Environment(DocumentImporter.self) private var importer
    @Query(sort: \Document.addedAt, order: .reverse) private var documents: [Document]

    @State private var showFilePicker = false
    @State private var showURLSheet = false
    @State private var showScanner = false
    @State private var urlText = ""
    @State private var selected: Document?
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            Group {
                if documents.isEmpty {
                    ContentUnavailableView(
                        "Nothing to listen to yet",
                        systemImage: "headphones",
                        description: Text("Add a PDF, an article link or a photo of a page.")
                    )
                } else {
                    List {
                        ForEach(documents) { doc in
                            Button { open(doc) } label: { DocumentRow(document: doc) }
                                .buttonStyle(.plain)
                                .accessibilityHint("Opens the player")
                        }
                        .onDelete { offsets in offsets.map { documents[$0] }.forEach(context.delete) }
                    }
                }
            }
            .navigationTitle("Library")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Settings", systemImage: "gearshape") { showSettings = true }
                }
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        Button("Import File", systemImage: "doc") { showFilePicker = true }
                        Button("Add Article Link", systemImage: "link") { showURLSheet = true }
                        Button("Scan Pages", systemImage: "camera.viewfinder") { showScanner = true }
                        Button("Paste Text", systemImage: "doc.on.clipboard") {
                            if let text = UIPasteboard.general.string { importer.importText(text) }
                        }
                    } label: { Label("Add", systemImage: "plus") }
                }
            }
            .fileImporter(isPresented: $showFilePicker, allowedContentTypes: [.pdf, .epub, .plainText]) { result in
                if case .success(let url) = result { Task { await importer.importFile(at: url) } }
            }
            .sheet(isPresented: $showURLSheet) { urlSheet }
            .sheet(isPresented: $showSettings) { SettingsView() }
            .sheet(isPresented: $showScanner) {
                ScannerView { images in
                    Task {
                        if let doc = try? await ScanImporter.document(from: images) { insert(doc) }
                    }
                }
            }
            .navigationDestination(item: $selected) { doc in PlayerView(document: doc) }
            .overlay { if importer.isImporting { ProgressView("Importing…").padding().background(.thinMaterial, in: .rect(cornerRadius: 12)) } }
            .alert("Couldn't import", isPresented: .constant(importer.lastError != nil)) {
                Button("OK") { importer.lastError = nil }
            } message: { Text(importer.lastError ?? "") }
            .onChange(of: importer.pending.count) { _, count in
                guard count > 0 else { return }
                let docs = importer.pending
                importer.pending.removeAll()
                docs.forEach { context.insert($0) }
                if let last = docs.last { open(last) }
            }
            .safeAreaInset(edge: .bottom) { if player.document != nil { MiniPlayerBar() } }
        }
    }

    private var urlSheet: some View {
        NavigationStack {
            Form {
                TextField("https://…", text: $urlText)
                    .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
            }
            .navigationTitle("Add Article")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        if let url = URL(string: urlText) { Task { await importer.importArticle(from: url) } }
                        showURLSheet = false; urlText = ""
                    }
                }
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { showURLSheet = false } }
            }
        }
        .presentationDetents([.fraction(0.3)])
    }

    private func insert(_ doc: Document) {
        context.insert(doc)
        open(doc)
    }

    private func open(_ doc: Document) {
        player.load(doc)
        selected = doc
    }
}

struct DocumentRow: View {
    let document: Document
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2).frame(width: 32)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 4) {
                Text(document.title).font(.headline).lineLimit(2)
                Text("\(document.estimatedMinutes) min · \(Int(document.progressFraction * 100))% done")
                    .font(.subheadline).foregroundStyle(.secondary)
            }
            Spacer()
            ProgressView(value: document.progressFraction).frame(width: 44)
                .accessibilityHidden(true)
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
    }
    private var icon: String {
        switch document.kind {
        case .pdf: "doc.richtext"
        case .epub: "book"
        case .article: "safari"
        case .text: "text.alignleft"
        case .scan: "camera.viewfinder"
        }
    }
}

struct MiniPlayerBar: View {
    @Environment(PlayerEngine.self) private var player
    var body: some View {
        HStack {
            Text(player.document?.title ?? "").lineLimit(1)
            Spacer()
            Button(action: player.toggle) {
                Image(systemName: player.isPlaying ? "pause.fill" : "play.fill").font(.title2)
            }
            .accessibilityLabel(player.isPlaying ? "Pause" : "Play")
        }
        .padding()
        .glassEffect(in: .rect(cornerRadius: 16))
        .padding(.horizontal)
    }
}
