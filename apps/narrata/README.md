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
NarrataTests/                 Swift Testing: text cleanup, HTML, EPUB fixture, article extraction
  Localizable.xcstrings       en source + de, fr, es, tr
```

## Device test and TestFlight (needs your Apple Developer account)

1. `xcodegen` then open `Narrata.xcodeproj`. In `project.yml` set `DEVELOPMENT_TEAM` to your
   Team ID (or pick the team in Signing & Capabilities for all four targets) and regenerate.
2. In App Store Connect › Identifiers, register `com.theoryofweb.narrata` with capabilities
   **App Groups** (`group.com.theoryofweb.narrata`) and **Siri**. The `.share` and `.widgets`
   identifiers need App Groups too. Xcode's automatic signing can create these for you.
3. Local Plus testing: Edit Scheme › Run › Options › StoreKit Configuration → `Narrata.storekit`.
   Products: `com.theoryofweb.narrata.plus.monthly` (4.99) and `.annual` (39.99), both with a
   1-week free trial. Create the same products in App Store Connect before TestFlight.
4. Run on a device (iOS 27) and verify, in this order:
   - Import a PDF from Files → plays, words highlight, Lock Screen shows controls, audio keeps
     playing with the screen locked.
   - Share a Safari article to Narrata → app opens with the article (`narrata://inbox`).
   - Scan a printed page with the camera → text reads correctly.
   - Settings › Voices lists Enhanced/Premium voices after downloading one in
     Settings › Accessibility › Spoken Content › Voices.
   - Apple Intelligence on: preview bullets appear on first open; long-press a paragraph →
     Simplify; Summarize in the toolbar.
   - Siri: "Search Narrata for <word>", "Open <title> in Narrata", and while playing: "pause",
     "skip forward" (Now Playing).
   - Add the Continue Listening widget; tap it → playback resumes.
   - VoiceOver on: swipe through the player, use the "Play from here" rotor action.
   - Settings › Accessibility › Display: Larger Text (XXL), Increase Contrast, Reduce Motion.
5. Archive → Distribute → TestFlight. Internal testers first, then the external group of
   dyslexic/ADHD readers with the questions in `../../research/listen-ai/apple-featuring-plan.md`.

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
