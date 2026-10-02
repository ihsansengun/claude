# Plan: ship a native iOS document-audio app in two weeks, aimed at the iOS 27 featuring wave

Written 2026-09-30. Replaces the earlier GAAD-2027 plan, which assumed a 5-month build.

## 1. The bet in one paragraph

Build a native SwiftUI iPhone app that turns documents (PDF, EPUB, articles, photos of pages)
into a listenable library with word highlighting, then submit it around **14 Oct 2026** with an
App Store featuring nomination filed the same day. The pitch to editors: a new indie app that
adopts the iOS 27 platform properly (Siri AI via App Schemas, Foundation Models with the free
Private Cloud Compute model, Liquid Glass, Accessibility Nutrition Labels) and treats accessibility
as core, with honest pricing. Featuring is a bonus (est. 10–20%); the reliable path is ASO plus
a small paid test after launch.

## 2. Featuring windows from today

| Window | Nomination type | Deadline | Notes |
|---|---|---|---|
| iOS 27 launch wave (OS shipped 14 Sep) | App Launch | file on submission day (2-week minimum lead) | editors run "updated for iOS 27 / works with Siri AI" collections for weeks after launch |
| Dyslexia & ADHD Awareness Month (October) | New Content + In-App Event | ~14 Oct | tight; only if v1 is on the store by ~24 Oct |
| Holiday / New Year collections | App Enhancement | late Oct–Nov | ship a 1.1 with one visible new feature |
| GAAD, 20 May 2027 | App Enhancement | ~18 Feb 2027 | the accessibility showcase; plan a 2.0 for it |

Nomination write-up (App Store Connect → Featuring Nominations): what it is in one sentence;
why now (iOS 27 adoption list); accessibility work and who tested it; privacy (on-device, no
account); target storefronts; up to 5 supplemental URLs (press kit, demo video).

## 3. Positioning (do not compete with Apple's Accessibility Reader)

Accessibility Reader (iOS 26, upgraded in iOS 27 with summaries, translation and content
cleanup) already is a system-wide reading mode for dyslexia/low vision. Editors won't feature a
copy of a system feature. We are the thing it isn't:

**A library and audio player for whole documents.** Import once, listen anywhere: progress per
document, background and Lock Screen playback, speed, sleep timer, chapters, Siri control,
export to audio, premium voices. "Turn your reading pile into a podcast queue."

Working name: **Narrata** (placeholder; check trademark and App Store search before keeping it).
Avoid "Listen AI": 5+ look-alikes on the store.

## 4. iOS 27 adoption list (what the nomination cites)

| Platform feature | How we use it | Ships in v1? |
|---|---|---|
| Foundation Models, on-device | "Simplify this paragraph", chapter titles, 3-bullet preview | yes |
| Foundation Models, Private Cloud Compute (free < 2M downloads, Small Business Program) | full-document summary, "ask this document" | yes, behind availability check |
| OCRTool system tool | photo of a page → text | yes |
| SpotlightSearchTool + Core Spotlight donations | search across the library, Siri search | yes (donations) / v1.1 (tool) |
| App Schemas, System domain (`searchInApp`, `open`) + Now Playing commands | "Search Narrata for…", "Open … in Narrata", voice play/pause/skip | yes |
| Onscreen awareness entities | "read this to me" on the open document | v1.1 |
| SwiftUI Document protocol, Liquid Glass (Xcode 27) | document import pipeline, native look for free | yes |
| Accessibility Nutrition Labels | VoiceOver, Voice Control, Larger Text, Dark, Differentiate Without Color, Contrast, Reduced Motion | yes, all seven |
| Translation framework | translate then listen | v1.1 |
| CarPlay audio | needs entitlement request; apply now | v1.2 |

Constraints found in research: third-party apps cannot use Siri voices; system enhanced
voices are the free tier; Personal Voice is for AAC apps, so no voice cloning.

## 5. Scope

### v1 (two weeks)
- Import: PDF (PDFKit), EPUB (unzip + XHTML strip), web article (share sheet + URL, readability
  pass), pasted text, photo of a page (OCRTool / Vision fallback), Files app
- Text cleanup: strip headers, footers, page numbers, hyphenation across lines
- Player: AVSpeechSynthesizer with word and sentence highlighting, 0.5–3× speed, skip sentence /
  paragraph, sleep timer, background audio, Now Playing / Lock Screen controls
- Reading view: font, size, line and letter spacing, themes with AA contrast, sentence-focus mode
- Intelligence: preview bullets, simplify paragraph, document summary (PCC when available)
- Library: SwiftData, progress per document, sort by recent, Spotlight donation
- Siri / Shortcuts: Audio App Schema, search-in-app, "Continue listening" intent; one widget
- Accessibility: all applicable labels, tested with VoiceOver and Voice Control
- Monetization: free = unlimited system voices + all accessibility; Plus = cloud voices with a
  visible meter + unlimited summaries. Monthly and annual only, StoreKit 2, no paywall before
  the first listen

### Not in v1
Cloud voices provider integration (design the meter now, wire the provider in 1.1), voice cloning,
podcast generation, iPad/Mac layouts (SwiftUI runs, not tuned), CarPlay, accounts, analytics SDKs.

## 5a. Progress (updated 2026-10-02)

- [x] Day 1–2: scaffold, SwiftData model, PDF + text import, player with highlighting — CI green on Xcode 27
- [x] Day 3–4: EPUB (ZIPFoundation), article, OCR scan, share sheet → inbox, text cleanup, Now Playing
- [x] Day 5–6: reading settings, 5 AA-contrast themes, sleep timer, speed; accessibility pass 1
- [x] Day 7–8: Foundation Models (on-device + PCC path), StoreKit 2 + visible meter
- [x] Day 9: App Intents (search schema, Continue Listening), Spotlight donation, widget
- [x] Day 9: Siri schemas — System domain (`searchInApp`, `open`); Audio domain dropped (music-service shape, not a reader fit)
- [x] Day 10: accessibility pass 2 (Dynamic Type scaling, Increase Contrast, VoiceOver paragraph labels, Reduce Motion)
- [x] Day 11: onboarding (3 screens, no paywall); App Store copy + nomination text drafted
- [ ] Day 12: TestFlight to dyslexic/ADHD readers — needs Apple Developer account + device build (steps in apps/narrata/README.md)
- [~] Day 13: placeholder icon in repo; privacy policy drafted (research/listen-ai/privacy-policy.md); screenshots + preview video still to capture on device
- [ ] Day 14: submit; file Featuring Nomination + In-App Event

## 6. Two-week schedule

| Day | Deliverable |
|---|---|
| 1–2 | Project from scaffold, SwiftData model, PDF + text import, basic player with highlighting |
| 3–4 | EPUB + article + OCR import, text cleanup, Now Playing / background audio |
| 5–6 | Reading view customization, themes, sleep timer, speed; accessibility pass 1 |
| 7–8 | Foundation Models features with availability fallbacks; StoreKit 2 + meter UI |
| 9 | App Intents: Audio schema, search, widget; Spotlight donations |
| 10 | Accessibility pass 2 (VoiceOver, Voice Control, Dynamic Type XXL, Reduce Motion); Nutrition Labels |
| 11 | Onboarding (3 screens, no paywall), App Store page: screenshots, preview video, copy in EN + 3 languages |
| 12 | TestFlight to 10–15 dyslexic/ADHD readers; fix list |
| 13 | Fixes, privacy manifest, "Data Not Collected" label, review notes |
| 14 | Submit; file Featuring Nomination (App Launch) + In-App Event for Awareness Month |

## 7. After launch (measure before scaling)
Spend a fixed $1–2K on Apple Search Ads in the US on 10 exact-match keywords. Track cost per
install, onboarding completion, first-listen rate, Plus trial start, trial → paid. Decide in
advance: scale if payback < 90 days, iterate if first-listen rate < 60%, stop if trial → paid < 3%.

## 8. Sources
- Nominations: https://developer.apple.com/help/app-store-connect/manage-featuring-nominations/nominate-your-app-for-featuring/
- Featuring criteria: https://developer.apple.com/app-store/getting-featured
- WWDC26 Foundation Models (241): https://developer.apple.com/videos/play/wwdc2026/241/
- WWDC26 PCC model (319): https://developer.apple.com/videos/play/wwdc2026/319/
- WWDC26 App Schemas (240): https://developer.apple.com/videos/play/wwdc2026/240/
- WWDC26 SwiftUI (269): https://developer.apple.com/videos/play/wwdc2026/269/
- Accessibility Reader: https://support.apple.com/guide/iphone/read-listen-text-apps-accessibility-reader-iph406a46ab8/ios
- Accessibility Nutrition Labels: https://support.apple.com/en-us/123073
- Siri voices not available to third parties: https://speechcentral.net/2026/08/08/why-cant-third-party-apps-use-siri-voices-on-iphone-ipad-and-mac/
- iOS 27 release: https://www.macrumors.com/2026/09/14/apple-releases-ios-27/
