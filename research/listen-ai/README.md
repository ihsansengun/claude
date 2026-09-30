# Listen AI: Text to Speech — competitor teardown

Target: `com.codespaceapps.listeningapp` (Google Play) / `id6502340091` (App Store).
Compiled 2026-09-30 from search-engine snippets of Google Play, App Store, APK mirrors,
Appllama and review sites, plus an AppMagic screenshot (section 1a). Google Play and the
App Store could not be fetched directly, so some numbers below disagree across sources;
ranges are given where they do.

## 1. Snapshot

| | Android | iOS |
|---|---|---|
| Listing name | Listen AI: Text to Speech | Text to Speech - Listen AI / Listen AI: PDF & Docs Reader (varies by storefront) |
| Publisher (now) | Deep Flow Apps — DEEP FLOW SOFTWARE SERVICES FZCO, Dubai Digital Park, UAE | DEEP FLOW SOFTWARE SERVICES |
| Original developer | Codespace Dijital Hizmetler A.Ş., Istanbul (APK signing cert still `CN=Codespace, L=Istanbul, C=TR`) | same |
| Launched | 2024 | September 2024 |
| Installs | ~6.6M lifetime (AppBrain); store copy claims "12M+ users" | — |
| Downloads, last 30 days | ~190K | ~40K (Appllama) |
| Rating | 4.4–4.5 ★, ~123K–127K reviews | ~4.5 ★, ~5.6K ratings (US) |
| Latest version | 2.5.6 (15 Sep 2026); releases every ~2–3 weeks | 2.5.5 |
| Size | APK 150–190 MB | 210.8 MB |
| Min OS | Android 7.0 | iOS 12.0 |
| Category | Productivity | Productivity |

Sister apps from the same Turkish team: Chatbot AI – Search Assistant (10M+ installs),
Smart Noter – AI Note Taker, Shots: Captions & Video Edit, Sparkle – Micro Learning Daily.
This is a **portfolio studio** that runs paid acquisition on subscription AI utilities, not a
single-product company.

### About "it's not on Apple"
It **is** on iOS, but iOS is its weak side: about 5× fewer monthly downloads than Android
and about 20× fewer ratings. The iOS store is also full of copycats using the same name
(`id6743119800` by Vladyslav Kulykevych, `id6753171019`, `id6756644157`,
"PDF Text to Speech：AI Listen", "ListenAloud"…). So there's still room on iOS, but only
for a clearly better product with a different name. Another "Listen AI" won't stand out.

## 1a. AppMagic (logged-out screenshot, 2026-09-30)

AppMagic only shows buckets when you're logged out, so these are lower bounds.

| Last 30 days | Value | Top countries |
|---|---|---|
| Revenue | **> $100,000** | 27% United States, then 7%, 4%, 4%, 3%, 3%, 3%, 49% others |
| Downloads | **> 100,000** | 12% Argentina (truncated "Arg…"), 9%, 9%, 8%, 8%, 6%, 4%, 44% others |

AppMagic lists the publisher under a Turkish flag (Deep Flow Software Services).

How to read it:
- The US brings 27% of revenue but under 12% of downloads, so a US user is worth several times the average user.
- The top download country is Argentina, a low-price market. This looks like cheap paid installs in LATAM and emerging markets, with the money made in the US and other rich markets.
- Revenue is spread across many countries (49% "others"), so localized voices and paywalls matter.
- The lower bounds fit the search data (~190K Android + ~40K iOS downloads a month). Revenue is probably low-to-mid six figures a month, but the upper bound is unknown.

## 2. Feature inventory (what we must match)

**Input sources**
- PDF, ePub, Word/DOCX, TXT, eBooks, academic papers
- Web pages / articles: built-in web reader, paste URL
- Paste or type text
- Camera scan: OCR from printed books and pages ("picture to speech")
- Google Drive import (users complain it asks for email access)
- Highlight text in another app or site → narrate (share / selection flow)

**Playback**
- "Premium" natural voices, 60+ languages and accents
- Word-by-word highlighting while reading
- Speed control up to 3×
- Background listening

**Output / library**
- Convert text to MP3, listen offline
- Personal audio library

**AI extras (used for upsell)**
- Voice cloning: record your voice and use it for narration. Some users say it disappeared from later builds
- AI podcast generator: turns notes, articles or prompts into a two-host style "show"

**Positioning:** students, busy professionals, accessibility (dyslexia, ADHD, low vision,
eye strain).

## 3. Monetization

- Freemium with a hard paywall shown during onboarding. Appllama captured 33 screens across onboarding, paywall and core tabs.
- Observed prices: **$4.99/week or $39.99/year** (iOS, Appllama). Users also report **$7.99/week** (~$416/yr) and **$12/week**, which suggests A/B-tested or regional price walls.
- **Undisclosed usage cap even on paid plans:** users hit a "weekly limit" after roughly 14–15 hours of audio, with no meter showing how much is left.
- The paywall shows "$7.99" prominently without making clear it's per week. This is the main source of refund requests (Speech Central wrote an article about it).

Why the cap exists (our estimate): speech runs ~150 wpm ≈ 54K characters per hour. Premium
cloud TTS costs about $30–100 per 1M characters at ElevenLabs-class quality, or roughly
$1.6–5.4 per listening hour. A 15 h/week heavy user costs $25–80/week, far more than $4.99.
So the cap is a cost control they chose not to show users.

## 4. What users hate (our opening)

From Play/App Store review snippets and third-party reviews:

1. **Pricing tricks**: weekly billing hidden, hard to cancel, "cancel anytime" isn't obvious
2. **Hidden weekly limit** on a paid plan, with no usage display
3. **Playback reliability**: narration stops every 30–45 s; 3-second pause at every period; voice "screams" or gets stuck on words at the end of long sentences (looks like chunk-boundary/streaming bugs)
4. **Download/MP3 export broken** for some users
5. **Features quietly removed** (voice cloning)
6. **Over-broad permissions** (email scope for Google Drive)
7. Large app size (150–210 MB)

The top review complaints are about **trust and reliability**, not missing features. That's
the easiest ground to beat them on.

## 5. Competitive landscape

| App | Price | Notes |
|---|---|---|
| Speechify | $139/yr or $29/mo; free tier | Market leader, 50M+ users claimed; heavy paid acquisition |
| ElevenReader (ElevenLabs) | Free 10 h/month; Ultra $11/mo or $99/yr | Best voices, generous free tier, owns its TTS model, so the lowest marginal cost |
| Listen AI | $4.99–12/wk, $39.99/yr | Cheap annual, predatory weekly |
| @Voice Aloud Reader | Free / low one-time | Android power-user favourite, uses system TTS |
| Speech Central | One-time / sub | Accessibility-focused; publicly positions against Listen AI |
| Listening.com | Sub | Academic papers niche + browser extension |

TTS market: roughly $4.4B (2026), heading toward about $12.5B by 2031 (Mordor Intelligence, via search).

## 6. How we build a better one (proposal)

**Differentiators**
1. **Honest pricing**: monthly and annual only, no weekly trap; a free tier that is useful by itself
2. **Visible usage meter** for premium voices; unlimited listening on on-device voices
3. **Hybrid TTS engine**: fast on-device neural voices (e.g. Kokoro, Piper-class models, or the OS neural voices) for free/unlimited use, and cloud premium voices for paid users. This removes the cost pressure behind the hidden cap
4. **Rock-solid playback**: sentence-level chunking with look-ahead prefetch, gapless audio, pause length tied to punctuation, a cached audio file per document so replay costs nothing
5. **Clean text extraction**: skip headers, footers, page numbers, citations and references (Listen AI's weak spot for academic PDFs)
6. **iOS-first polish**: Share Extension, Safari extension, Lock Screen and Live Activity controls, CarPlay, Siri/Shortcuts
7. **Useful AI** (paid tier): summarize before listening, chat with the document, "podcast mode", translate and listen

**MVP scope (v1)**
- Import: PDF, EPUB, DOCX, TXT, URL, share sheet, camera OCR (Apple Vision / ML Kit, on-device)
- Player: highlight-follow, 0.5–3× speed, skip sentence/paragraph, sleep timer, background audio
- Voices: on-device free + 1 cloud provider premium
- Library with progress sync, offline MP3/M4A export
- Paywall: annual and monthly, 7-day trial, usage meter

**v2**: voice cloning (with consent flow), podcast generator, browser extension/web app,
Readwise/Pocket/Kindle-highlights import.

**Stack suggestion**: Flutter or React Native for both stores, RevenueCat for subscriptions,
native modules for on-device TTS and OCR, and a thin backend that proxies cloud TTS and
caches rendered audio per (document, voice, chunk).

## 7. Verdict: is it worth building?

**Yes, as a small, time-boxed bet aimed at the US on iOS first. Not as a straight clone.**

Reasons to build:
- Demand is proven: a two-year-old utility from a small studio makes > $100K a month, and Speechify and ElevenReader show the category supports much bigger players.
- The incumbent is beatable on trust: most complaints are about hidden weekly pricing, a hidden cap and buggy playback. There's no technical moat.
- Its iOS version is weak even though the US (where iOS monetizes best) is its biggest revenue market.
- Build cost is low: TTS APIs, on-device voices and OCR are off the shelf, so an MVP takes weeks.
- Voice costs keep falling, which makes an honest "unlimited on-device + metered premium" model workable.

Risks:
- **Distribution is the whole game.** Listen AI grows through paid installs and store search (ASO), not product quality. Without an ad budget or an organic channel (TikTok/short video, SEO, student communities), a better app still won't get found.
- Free alternatives are getting good: ElevenReader gives 10 free hours a month with top voices, and Chrome, Android and iOS have built-in read-aloud. NotebookLM-style audio overviews cover the "podcast" use.
- The store is crowded with look-alike "Listen AI" clones, so generic keywords are expensive.
- Heavy listeners cost real money on cloud voices. Pricing has to cover them without a hidden cap.

How to make it a better bet:
1. **Pick a wedge.** For example, students and academic PDFs (clean extraction, citation skipping, summaries), dyslexia/ADHD, or a language where good voices are rare. Compete on that niche's keywords instead of "text to speech".
2. **iOS first, US/English first**, then localize paywalls for the top revenue markets.
3. **Honest pricing as the hook:** annual plus monthly, a visible meter, unlimited on-device voices.
4. **Test before scaling.** After the MVP, spend a small fixed ad budget (e.g. $2–5K) to measure cost per install, trial start rate, trial-to-paid rate and payback period. Set kill or scale thresholds in advance.

## 8. Open data gaps

- Exact revenue and downloads (AppMagic logged-in; the logged-out view only shows "> $100K" / "> 100K")
- Names of countries 2–7 in both splits (hover the bars in AppMagic)
- Android vs iOS split (AppMagic "2 apps summary")
- Exact paywall and onboarding flow (Appllama has the screenshots)
- Which TTS provider they use (would need APK inspection)

## Sources

- Google Play listing — https://play.google.com/store/apps/details?id=com.codespaceapps.listeningapp
- App Store listing — https://apps.apple.com/us/app/text-to-speech-listen-ai/id6502340091
- AppBrain — https://www.appbrain.com/app/listen-ai-text-to-speech/com.codespaceapps.listeningapp
- AppBrain, Codespace Dijital developer page — https://www.appbrain.com/dev/Codespace+Dijital/
- APKMirror (Deep Flow Apps, signing cert) — https://www.apkmirror.com/apk/deep-flow-apps/listen-ai-text-to-speech/
- Appllama (downloads, pricing, publisher, screens) — https://appllama.io/apps/6502340091/text-to-speech-listen-ai
- Speech Central review (pricing, weekly limit, refunds) — https://speechcentral.net/2025/06/07/listen-ai-app-review-why-users-are-seeking-refunds-better-alternatives/
- reviewed.app — https://reviewed.app/app/listen-ai-text-to-speech/
- Apptail, Codespace developer — https://apptail.io/developer/codespace-dijital-hizmetler-anonim-sirketi-ANF
- ElevenReader pricing — https://elevenreader.io/blog/best-pricing-more-value
- Speechify pricing 2026 — https://costbench.com/software/ai-voice-tools/speechify/
- Speechify/TTS cost & market — https://getlatka.com/companies/speechify.com , https://app.dealroom.co/news/note/1-000-ai-ads-a-day-and-tokens-over-salaries-inside-speechify-s-playbook-for-owning-the-voice-ai-market
