import Testing
@testable import Narrata

struct TextCleanerTests {
    @Test func stripsRepeatedHeadersAndPageNumbers() {
        let pages = (1...4).map { "Journal of Things\nBody sentence number \($0). Another one here.\n\($0)" }
        let s = TextCleaner.sentences(from: pages)
        #expect(!s.contains { $0.text.contains("Journal of Things") })
        #expect(!s.contains { $0.text == "3" })
        #expect(s.count == 8)
    }

    @Test func joinsHyphenatedLineBreaks() {
        let s = TextCleaner.sentences(from: ["This is inter-\nnational news."])
        #expect(s.first?.text == "This is international news.")
    }

    @Test func keepsParagraphIndexes() {
        let s = TextCleaner.sentences(fromPlainText: "First para. Still first.\n\nSecond para.")
        #expect(s.map(\.paragraphIndex) == [0, 0, 1])
    }
}
