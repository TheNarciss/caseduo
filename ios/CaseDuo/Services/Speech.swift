import AVFoundation
import Observation
import Speech

/// Dictation, because interviews are spoken. On-device recognition when the phone supports it
/// for the language (no time limit); otherwise Apple's server, whose tasks stop after about a
/// minute: the task is restarted before that and the text keeps growing.
@MainActor
@Observable
final class Dictation {
    enum State: Equatable {
        case idle
        case recording
        case denied(String)
        case unavailable(String)
    }

    private(set) var state: State = .idle
    /// Everything said so far, finished segments and the current one.
    private(set) var transcript = ""

    @ObservationIgnored private var committed = ""
    @ObservationIgnored private var partial = ""
    @ObservationIgnored private let audioEngine = AVAudioEngine()
    @ObservationIgnored private var request: SFSpeechAudioBufferRecognitionRequest? {
        didSet { buffers.set(request) }
    }
    /// The audio tap runs on the audio thread: it reaches the current request through this box.
    @ObservationIgnored private let buffers = RequestBox()
    @ObservationIgnored private var task: SFSpeechRecognitionTask?
    @ObservationIgnored private var recognizer: SFSpeechRecognizer?
    @ObservationIgnored private var restartTimer: Timer?
    @ObservationIgnored private var onDevice = false

    var isRecording: Bool { state == .recording }

    static func locale(for language: String) -> Locale {
        language == "en" ? Locale(identifier: "en-GB") : Locale(identifier: "fr-FR")
    }

    /// Starts listening, appending to `existing` (what is already in the answer field).
    func start(language: String, existing: String = "") async {
        guard state != .recording else { return }
        guard await Self.requestPermissions() else {
            state = .denied("Autorise le micro et la reconnaissance vocale dans Réglages > CaseDuo.")
            return
        }
        let recognizer = SFSpeechRecognizer(locale: Self.locale(for: language))
        guard let recognizer, recognizer.isAvailable else {
            state = .unavailable("La dictée n'est pas disponible pour le moment.")
            return
        }
        self.recognizer = recognizer
        onDevice = recognizer.supportsOnDeviceRecognition
        committed = existing.isEmpty ? "" : existing + (existing.hasSuffix(" ") || existing.hasSuffix("\n") ? "" : " ")
        partial = ""
        transcript = existing
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
            try session.setActive(true, options: .notifyOthersOnDeactivation)
            let input = audioEngine.inputNode
            let format = input.outputFormat(forBus: 0)
            input.removeTap(onBus: 0)
            let box = buffers
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
                box.append(buffer)
            }
            audioEngine.prepare()
            try audioEngine.start()
            beginTask()
            state = .recording
        } catch {
            stopAudio()
            state = .unavailable("Impossible de démarrer le micro : \(error.localizedDescription)")
        }
    }

    func stop() {
        guard state == .recording else { return }
        request?.endAudio()
        commitPartial()
        stopAudio()
        state = .idle
    }

    /// Clears what was dictated (used when the answer field is reset).
    func reset(to text: String = "") {
        committed = text
        partial = ""
        transcript = text
    }

    private func beginTask() {
        guard let recognizer else { return }
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        request.taskHint = .dictation
        request.addsPunctuation = true
        if onDevice { request.requiresOnDeviceRecognition = true }
        self.request = request
        task = recognizer.recognitionTask(with: request) { [weak self] result, error in
            let text = result?.bestTranscription.formattedString
            let isFinal = result?.isFinal ?? false
            Task { @MainActor in
                guard let self else { return }
                if let text {
                    self.partial = text
                    self.transcript = self.committed + text
                }
                if isFinal || error != nil {
                    // Server tasks end on their own around a minute: keep going while recording.
                    if self.state == .recording, !self.onDevice {
                        self.commitPartial()
                        self.restartTask()
                    }
                }
            }
        }
        restartTimer?.invalidate()
        if !onDevice {
            restartTimer = Timer.scheduledTimer(withTimeInterval: 55, repeats: false) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.state == .recording else { return }
                    self.request?.endAudio()
                }
            }
        }
    }

    private func restartTask() {
        task?.cancel()
        task = nil
        beginTask()
    }

    private func commitPartial() {
        guard !partial.isEmpty else { return }
        committed += partial + " "
        partial = ""
        transcript = committed
    }

    private func stopAudio() {
        restartTimer?.invalidate()
        restartTimer = nil
        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        task?.cancel()
        task = nil
        request = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        try? AVAudioSession.sharedInstance().setCategory(.ambient, options: [.mixWithOthers])
    }

    static func requestPermissions() async -> Bool {
        let speech = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0 == .authorized) }
        }
        guard speech else { return false }
        return await AVAudioApplication.requestRecordPermission()
    }
}

/// The recognition request, shared with the audio thread under a lock.
private final class RequestBox: @unchecked Sendable {
    private let lock = NSLock()
    private var request: SFSpeechAudioBufferRecognitionRequest?

    func set(_ request: SFSpeechAudioBufferRecognitionRequest?) {
        lock.lock()
        self.request = request
        lock.unlock()
    }

    func append(_ buffer: AVAudioPCMBuffer) {
        lock.lock()
        request?.append(buffer)
        lock.unlock()
    }
}
