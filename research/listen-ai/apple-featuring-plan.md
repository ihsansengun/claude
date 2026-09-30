# Plan: an iOS reading app built to get featured by Apple

**Goal:** get editorially featured on the App Store (a Today story, an accessibility/GAAD
collection, or App of the Day). Stretch goal: Apple Design Award finalist, Inclusivity.

**Target moment:** Global Accessibility Awareness Day, **Thursday 20 May 2027**.
Nomination due by **~18 Feb 2027** (Apple recommends up to 3 months ahead; the minimum is 2 weeks).

This changes the earlier teardown (`README.md`) in two ways:
- Build **native Swift/SwiftUI, iOS/iPadOS/macOS**, not Flutter or React Native. Editors reward apps that adopt the latest Apple technologies well, and cross-platform frameworks lag on that.
- **Being featured comes first.** Pricing and design choices favour what editors reward over maximum short-term revenue.

---

## 1. Concept

A reading companion for people with dyslexia and ADHD that reads text aloud and
highlights it on screen at the same time. It turns any PDF, web page, photo of a page or
note into text you can listen to and follow along with. Everything runs on-device and
privately by default.

Working name: TBD. Avoid "Listen AI"; the store has 5+ look-alikes.

Why this concept fits: Listen AI shows the demand (> $100K/month), and it is the
opposite of what Apple features (weekly paywall, hidden caps, Flutter-style UI). The
2026 ADA Inclusivity winner (Guitar Wiz) won by building on Dynamic Type, Increased
Contrast and Differentiate Without Color. That's the same kind of work we'd do.

## 2. Apple's featuring criteria → what we build

Apple lists what editors look for:

| Criterion | Our answer |
|---|---|
| **User experience** | Open app → import anything → listening in < 5 s. Resume where you left off everywhere (iCloud sync). No account needed |
| **UI design** | SwiftUI + Liquid Glass. The reading view is the hero: calm, customizable, beautiful typography |
| **Innovation** | On-device Foundation Models to simplify, summarize or define hard words while you listen; multimodal OCR on photos of pages; Siri AI app actions ("read me this article") |
| **Uniqueness** | Multisensory reading (sound + highlight + focus tools) built with dyslexic/ADHD readers, not a generic TTS player |
| **Accessibility** | Full support for all applicable Accessibility Nutrition Labels, designed in from day one (section 4) |
| **Localization** | Launch in 5–6 languages (UI + voices + App Store page), chosen from top revenue storefronts |
| **Product page** | Screenshots showing real reading moments, an app preview video, In-App Events, and good ratings from the beta group |

## 3. Features

### MVP (launch)
- **Import:** PDF (PDFKit), EPUB, web pages (Share Extension + Safari Web Extension), paste text, camera/photo of a page (VisionKit / Vision OCR), Files and iCloud Drive
- **Listen:** system neural voices via `AVSpeechSynthesizer` (free, offline, unlimited), word- and sentence-level highlight sync, 0.5–3× speed, skip by sentence or paragraph, sleep timer, Lock Screen / Now Playing, background audio
- **Read-along view:** font, size, letter/line/word spacing, background tint and contrast presets, reading ruler / line focus, one-sentence-at-a-time mode
- **Understand (on-device Foundation Models):** "simplify this paragraph", 3-bullet summary before you start, tap a word to get a definition and hear it spoken
- **Clean text:** strip headers, footers, page numbers and citation clutter from PDFs
- **Library:** progress, iCloud sync, reading streaks without guilt-tripping notifications
- **System integration:** App Intents (Siri / Shortcuts: "read my latest import"), widgets ("continue listening"), iPad + Mac from the same codebase

### After launch (timed to later featuring moments)
- Premium cloud voices (the paid tier, metered with a visible meter)
- Apple Pencil point-to-read on iPad
- Translate + listen (Translation framework)
- CarPlay audio (needs entitlement)
- Focus timer / Pomodoro for ADHD study sessions
- Adopt WWDC27 APIs by iOS 28 launch day (September 2027 nomination)

### Deliberately not doing
- **Voice cloning via Personal Voice.** Apple's guidance aims it at assistive-communication (AAC) apps; a general reader asking for it risks review trouble and looks off-brand
- **Hard paywall in onboarding, weekly plans, fake "limited offer" timers**
- **Account wall, tracking SDKs, ad networks.** We want a "Data Not Collected" privacy label

## 4. Accessibility checklist (the core of the pitch)

Accessibility Nutrition Labels, declared truthfully and tested:
- [ ] VoiceOver: every control labelled, logical order, custom rotor for sentences/paragraphs
- [ ] Voice Control: all actions reachable by name
- [ ] Larger Text: Dynamic Type up to the largest accessibility sizes without truncation
- [ ] Dark Interface
- [ ] Differentiate Without Color Alone: highlight uses shape/underline as well as colour
- [ ] Sufficient Contrast: every theme passes WCAG AA; high-contrast themes available
- [ ] Reduced Motion: highlight animation respects the setting
- [ ] Captions / Audio Descriptions: only if we ship video (the onboarding video gets captions)

Also: Bold Text, Increase Contrast, Smart Invert, Switch Control testing, Assistive Access
review.

Process: recruit **15–20 dyslexic and ADHD readers** (students and adults) as TestFlight
testers from October. Aim for a partnership or quote from a dyslexia organisation. Editors
value the human story behind the app, and this is it.

Wording rule: "helps you read, understand and focus", never "treats" or "cures" anything.

## 5. Business model (compatible with featuring)

- **Free:** unlimited on-device voices, all accessibility features, import, basic AI tools. Accessibility is never paywalled
- **Plus (annual or monthly, ~$4.99/mo / ~$39.99/yr to start):** premium cloud voices with a visible meter, unlimited AI summaries, advanced export, cloud-voice MP3 export
- Soft upsell after value is shown, never before the first listen
- Consider a student discount and a family plan

Free on-device voices keep costs near zero, so there's no hidden cap. That fixes Listen AI's
biggest problem at the root.

## 6. Timeline to GAAD 2027

| When | Milestone |
|---|---|
| **Oct 2026** | 10 user interviews (dyslexic/ADHD readers); clickable prototype of the reading view; pick name + launch languages |
| **Nov–Dec 2026** | Build MVP: import → listen → highlight → customize; Foundation Models features; TestFlight to testers |
| **Jan 2027** | Accessibility audit against section 4; localization; iPad/Mac polish; widgets + App Intents |
| **by 18 Feb 2027** | **Submit Featuring Nomination** (App Store Connect): app launch, preferred date GAAD week, with the story, accessibility work and tester quotes |
| **Mar 2027** | Product page: screenshots, preview video, localized copy; press kit; submit for review |
| **Early Apr 2027** | Launch, so ratings and reviews build up before GAAD |
| **May 2027** | GAAD In-App Event (e.g. "Accessible Reading Week"); press outreach |
| **Jun 2027** | WWDC27: adopt new APIs right away → nominate for iOS 28 launch (Sept) |
| **Aug 2027** | Back to School nomination (students) |
| **Oct 2027** | Dyslexia & ADHD Awareness Month nomination + In-App Event |

## 7. Nomination write-up (draft outline)

1. **What it is:** one sentence
2. **Who it's for, and why we built it:** founder story, tester quotes
3. **Accessibility work:** labels supported, what we tested and with whom
4. **Apple technologies used:** Foundation Models, Vision, App Intents/Siri, Liquid Glass, widgets, iPad/Mac
5. **Privacy:** on-device, no account, Data Not Collected
6. **Timing:** why GAAD, and the In-App Event we're running
7. **Localization:** languages at launch

## 8. Decisions needed

- Primary audience: dyslexia + ADHD together, or lead with one?
- Launch languages (5–6)
- App name
- Team: who builds iOS natively (Swift/SwiftUI experience needed)
- Mac at launch, or iPhone + iPad only

## Sources

- Apple, Getting featured on the App Store — https://developer.apple.com/app-store/getting-featured
- Apple, Featuring nominations template — https://developer.apple.com/help/app-store-connect/reference/nominations/nominations-template
- Nomination lead times — https://www.apptweak.com/en/aso-blog/how-to-get-your-app-featured-on-the-app-store
- Accessibility Nutrition Labels — https://support.apple.com/en-us/123073 , https://developer.apple.com/videos/play/tech-talks/111433/
- WWDC26 intelligence frameworks — https://www.apple.com/newsroom/2026/06/apple-aids-app-development-with-new-intelligence-frameworks-and-advanced-tools/
- Foundation Models (WWDC26) — https://developer.apple.com/videos/play/wwdc2026/241/
- Personal Voice guidance — https://developer.apple.com/videos/play/wwdc2023/10033/ , https://blakecrosley.com/blog/accessibility-platform-features
- 2026 Apple Design Awards — https://www.apple.com/newsroom/2026/06/apple-reveals-winners-of-the-2026-apple-design-awards/
