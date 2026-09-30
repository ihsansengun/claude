# Narrata (working name)

Native iOS 27 app that turns documents into a listenable library: PDF, EPUB, articles, scans and
pasted text, read aloud with word highlighting. Plan and rationale: `../../research/listen-ai/`.

## Generate the Xcode project (Mac, Xcode 27)

```sh
brew install xcodegen
cd apps/narrata
xcodegen                    # writes Narrata.xcodeproj from project.yml
open Narrata.xcodeproj
```

Then in Xcode: set your team in Signing & Capabilities, change `com.yourcompany` in
`project.yml` (bundle IDs, App Group, product IDs) and regenerate.

## Layout

```
Narrata/
  NarrataApp.swift            entry, SwiftData container
  Models/Document.swift       library item = title + sentences + progress
  Import/                     PDFKit, EPUB (stub), article fetch, Vision OCR, text cleanup
  Player/PlayerEngine.swift   AVSpeechSynthesizer, sentence-at-a-time, Now Playing, remote commands
  Intelligence/               Foundation Models: preview, simplify, summary (all with fallbacks)
  Intents/                    App Intents + Shortcuts (Audio App Schema to add on day 9)
  Views/                      Library, Player (highlighting), Reading settings, Scanner
  Store/Store.swift           StoreKit 2, monthly/annual Plus, visible cloud-voice meter
NarrataShare/                 share-sheet extension → App Group inbox
NarrataWidgets/               "Continue listening" widget
NarrataTests/                 Swift Testing, text cleanup
```

## Known gaps (tracked in the two-week schedule)
- EPUB import needs ZIPFoundation (day 3). Share extension needs the URL-scheme hand-off (day 3).
- Foundation Models calls were written from WWDC26 session notes; confirm `LanguageModelSession`,
  `PrivateCloudComputeLanguageModel` and `OCRTool` signatures against the SDK (day 7).
- Audio App Schema and `system.searchInApp` annotations (day 9).
- Widget timeline reads placeholder data (day 9).
- Cloud voice provider not wired; the meter and entitlement exist (v1.1).

This scaffold was written without access to Xcode, so expect a first round of compiler
fixes on day 1, mostly around iOS 27 API names.
