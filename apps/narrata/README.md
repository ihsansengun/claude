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

Then in Xcode: set your team in Signing & Capabilities, the bundle ID is `com.theoryofweb.narrata` (set in
`project.yml`; App Group `group.com.theoryofweb.narrata`, product IDs `com.theoryofweb.narrata.plus.*`).

## Layout

```
Narrata/
  NarrataApp.swift            entry, SwiftData container
  Models/Document.swift       library item = title + sentences + progress
  Import/                     PDFKit, EPUB (ZIPFoundation), article fetch, Vision OCR, text cleanup
  Player/PlayerEngine.swift   AVSpeechSynthesizer, sentence-at-a-time, Now Playing, remote commands
  Intelligence/               Foundation Models: preview, simplify, summary (all with fallbacks)
  Intents/                    App Intents, Shortcuts, Siri System schemas (searchInApp, open), Spotlight
  Views/                      Library, Player (highlighting), Reading settings, Scanner
  Store/Store.swift           StoreKit 2, monthly/annual Plus, visible cloud-voice meter
NarrataShare/                 share-sheet extension → App Group inbox
NarrataWidgets/               "Continue listening" widget
NarrataTests/                 Swift Testing, text cleanup
```

## CI

`.github/workflows/narrata-ios.yml` builds and runs the unit tests on GitHub's `xcode-27` macOS
runner for every push touching `apps/narrata/`. `scripts/build.sh build|test` is the same command
used locally. Build logs are uploaded as an artifact on failure.

## Known gaps
- Siri: the iOS 27 Audio App Schema domain is a music-service shape (queues, stations,
  affinity), so Narrata adopts the System domain schemas `searchInApp` and `open` plus regular
  App Intents; voice play/pause/skip comes from Now Playing remote commands.
- Widget deep link `narrata://continue` and share-sheet hand-off `narrata://inbox` need a device
  test; simulators don't exercise the share extension's responder-chain `open`.
- Cloud voice provider not wired; the Plus entitlement and usage meter exist (v1.1).
- Screenshots, app icon and preview video are not in the repo yet.
