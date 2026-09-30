import Foundation
import AVFoundation
import MediaPlayer
import Observation

/// Sentence-at-a-time playback on AVSpeechSynthesizer with word-level highlight callbacks.
/// Speaking one sentence per utterance (instead of the whole document) is what avoids the
/// "stops every 30–45 s" and "stuck on a word" failures users report in Listen AI.
@Observable
@MainActor
final class PlayerEngine: NSObject {
    private(set) var document: Document?
    private(set) var isPlaying = false
    private(set) var currentSentence = 0
    /// Range of the word being spoken, inside the current sentence's text.
    private(set) var currentWordRange: Range<String.Index>?
    var rate: Float = 1.0 { didSet { if isPlaying { restartCurrentSentence() } } }
    var voice: AVSpeechSynthesisVoice? = VoiceCatalog.preferred()
    var sleepTimer: SleepTimer?

    private let synthesizer = AVSpeechSynthesizer()

    override init() {
        super.init()
        synthesizer.delegate = self
        configureAudioSession()
        configureRemoteCommands()
    }

    // MARK: - Public controls

    func load(_ document: Document) {
        stop()
        self.document = document
        currentSentence = min(document.progressSentence, max(0, document.sentences.count - 1))
        document.lastOpenedAt = .now
        updateNowPlaying()
    }

    func play() {
        guard let document, currentSentence < document.sentences.count else { return }
        if synthesizer.isPaused {
            synthesizer.continueSpeaking()
        } else {
            speak(sentence: document.sentences[currentSentence])
        }
        isPlaying = true
        updateNowPlaying()
    }

    func pause() {
        synthesizer.pauseSpeaking(at: .word)
        isPlaying = false
        persistProgress()
        updateNowPlaying()
    }

    func toggle() { isPlaying ? pause() : play() }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        isPlaying = false
        currentWordRange = nil
        persistProgress()
    }

    func seek(toSentence index: Int) {
        guard let document else { return }
        currentSentence = max(0, min(index, document.sentences.count - 1))
        currentWordRange = nil
        if isPlaying { restartCurrentSentence() }
        persistProgress()
    }

    func skipSentence(_ delta: Int) { seek(toSentence: currentSentence + delta) }

    func skipParagraph(_ delta: Int) {
        guard let document else { return }
        let current = document.sentences[currentSentence].paragraphIndex
        let target = current + delta
        if let idx = document.sentences.firstIndex(where: { $0.paragraphIndex == target }) {
            seek(toSentence: idx)
        }
    }

    // MARK: - Internals

    private func speak(sentence: Sentence) {
        let utterance = AVSpeechUtterance(string: sentence.text)
        utterance.voice = voice
        // AVSpeechUtteranceDefaultSpeechRate ≈ 0.5 maps to "1×" for most voices.
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate * rate
        utterance.postUtteranceDelay = 0.12   // short, fixed pause between sentences
        synthesizer.speak(utterance)
    }

    private func restartCurrentSentence() {
        synthesizer.stopSpeaking(at: .immediate)
        guard let document, currentSentence < document.sentences.count else { return }
        speak(sentence: document.sentences[currentSentence])
    }

    private func persistProgress() {
        document?.progressSentence = currentSentence
    }

    private func configureAudioSession() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? session.setActive(true)
    }

    private func configureRemoteCommands() {
        let center = MPRemoteCommandCenter.shared()
        center.playCommand.addTarget { [weak self] _ in Task { @MainActor in self?.play() }; return .success }
        center.pauseCommand.addTarget { [weak self] _ in Task { @MainActor in self?.pause() }; return .success }
        center.togglePlayPauseCommand.addTarget { [weak self] _ in Task { @MainActor in self?.toggle() }; return .success }
        center.nextTrackCommand.addTarget { [weak self] _ in Task { @MainActor in self?.skipParagraph(1) }; return .success }
        center.previousTrackCommand.addTarget { [weak self] _ in Task { @MainActor in self?.skipParagraph(-1) }; return .success }
    }

    private func updateNowPlaying() {
        guard let document else { return }
        MPNowPlayingInfoCenter.default().nowPlayingInfo = [
            MPMediaItemPropertyTitle: document.title,
            MPMediaItemPropertyArtist: "Narrata",
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? Double(rate) : 0,
            MPNowPlayingInfoPropertyPlaybackProgress: document.progressFraction,
        ]
    }
}

extension PlayerEngine: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, willSpeakRangeOfSpeechString characterRange: NSRange, utterance: AVSpeechUtterance) {
        let text = utterance.speechString
        Task { @MainActor in
            self.currentWordRange = Range(characterRange, in: text)
        }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            guard self.isPlaying, let document = self.document else { return }
            if self.sleepTimer?.isExpired == true {
                self.pause(); return
            }
            let next = self.currentSentence + 1
            if next < document.sentences.count {
                self.currentSentence = next
                self.speak(sentence: document.sentences[next])
                if next % 10 == 0 { self.persistProgress() }
            } else {
                self.isPlaying = false
                self.currentWordRange = nil
                self.persistProgress()
            }
        }
    }
}

struct SleepTimer {
    let endsAt: Date
    var isExpired: Bool { Date.now >= endsAt }
    init(minutes: Int) { endsAt = .now.addingTimeInterval(Double(minutes) * 60) }
}

enum VoiceCatalog {
    /// Highest-quality installed voice for the user's language; users can download
    /// "Enhanced"/"Premium" voices in Settings → Accessibility → Spoken Content.
    static func preferred(language: String = Locale.preferredLanguages.first ?? "en-US") -> AVSpeechSynthesisVoice? {
        let candidates = AVSpeechSynthesisVoice.speechVoices()
            .filter { $0.language.hasPrefix(String(language.prefix(2))) }
            .filter { !$0.voiceTraits.contains(.isPersonalVoice) }   // Personal Voice is for AAC apps
        return candidates.max { $0.quality.rawValue < $1.quality.rawValue }
            ?? AVSpeechSynthesisVoice(language: language)
    }

    static func all() -> [AVSpeechSynthesisVoice] {
        AVSpeechSynthesisVoice.speechVoices()
            .filter { !$0.voiceTraits.contains(.isPersonalVoice) }
            .sorted { ($0.language, $1.quality.rawValue) < ($1.language, $0.quality.rawValue) }
    }
}
