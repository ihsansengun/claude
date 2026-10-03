import Testing
import Foundation
import ZIPFoundation
@testable import Narrata

struct ArticleImporterTests {
    @Test func prefersArticleBodyAndDecodesTitle() {
        let html = """
        <html><head><title>Hello &amp; welcome</title></head>
        <body><nav>Menu Menu</nav><article><p>First sentence here. Second one.</p></article>
        <footer>Copyright</footer></body></html>
        """
        let (title, text) = ArticleImporter.extract(html: html, fallbackTitle: "x")
        #expect(title == "Hello & welcome")
        #expect(text == "First sentence here. Second one.")
    }

    @Test func fallsBackToWholePageWithoutArticle() {
        let html = "<html><body><div><p>Only paragraph.</p></div></body></html>"
        let (_, text) = ArticleImporter.extract(html: html, fallbackTitle: "site")
        #expect(text == "Only paragraph.")
    }
}

struct EPUBImporterTests {
    /// Builds a minimal EPUB 3 in a temp directory: container → OPF → two spine chapters.
    private func makeEPUB() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "test-\(UUID().uuidString).epub")
        let archive = try Archive(url: url, accessMode: .create)
        func add(_ path: String, _ content: String) throws {
            let data = Data(content.utf8)
            try archive.addEntry(with: path, type: .file, uncompressedSize: Int64(data.count)) { position, size in
                data.subdata(in: Int(position)..<Int(position) + size)
            }
        }
        try add("mimetype", "application/epub+zip")
        try add("META-INF/container.xml", """
        <?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>
        """)
        try add("OEBPS/content.opf", """
        <?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Test Book</dc:title><dc:identifier id="id">x</dc:identifier></metadata>
        <manifest>
          <item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
          <item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
        </manifest>
        <spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>
        """)
        try add("OEBPS/ch1.xhtml", "<html><body><h1>One</h1><p>Chapter one starts. It continues.</p></body></html>")
        try add("OEBPS/ch2.xhtml", "<html><body><p>Chapter two ends.</p></body></html>")
        return url
    }

    @Test func readsTitleAndSpineOrder() throws {
        let url = try makeEPUB()
        defer { try? FileManager.default.removeItem(at: url) }
        let doc = try EPUBImporter.document(from: url, title: "fallback")
        #expect(doc.title == "Test Book")
        #expect(doc.kind == .epub)
        #expect(doc.sentences.map(\.text) == ["One", "Chapter one starts.", "It continues.", "Chapter two ends."])
        #expect(doc.sentences.last?.paragraphIndex == 2)
    }
}
