import AVFoundation
import Foundation

@MainActor
final class AnnotationRecorder: NSObject, ObservableObject, AVAudioRecorderDelegate {
    @Published private(set) var isRecording = false
    @Published private(set) var elapsedTime = 0.0

    private var recorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var timer: Timer?
    private var completion: ((URL, Double) -> Void)?

    func requestPermissionAndStart(in folder: URL, completion: @escaping (URL, Double) -> Void, onDenied: @escaping (String) -> Void) {
        let session = AVAudioSession.sharedInstance()
        switch session.recordPermission {
        case .granted:
            start(in: folder, completion: completion, onDenied: onDenied)
        case .denied:
            onDenied("Microphone access is denied. Enable it in Settings to record annotations.")
        case .undetermined:
            session.requestRecordPermission { [weak self] granted in
                Task { @MainActor in
                    guard let self else { return }
                    if granted {
                        self.start(in: folder, completion: completion, onDenied: onDenied)
                    } else {
                        onDenied("Microphone access is required to record an annotation.")
                    }
                }
            }
        @unknown default:
            onDenied("The microphone permission state is unavailable.")
        }
    }

    func stop() {
        recorder?.stop()
    }

    func cancel() {
        recorder?.stop()
        if let recordingURL {
            try? FileManager.default.removeItem(at: recordingURL)
        }
        reset()
    }

    private func start(in folder: URL, completion: @escaping (URL, Double) -> Void, onDenied: @escaping (String) -> Void) {
        do {
            let audioFolder = folder.appendingPathComponent("audio", isDirectory: true)
            try FileManager.default.createDirectory(at: audioFolder, withIntermediateDirectories: true)
            let url = audioFolder.appendingPathComponent("annotation-\(UUID().uuidString).m4a")
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)
            let recorder = try AVAudioRecorder(url: url, settings: [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 44_100,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ])
            recorder.delegate = self
            recorder.prepareToRecord()
            guard recorder.record() else {
                onDenied("The microphone could not start recording.")
                return
            }
            self.recorder = recorder
            recordingURL = url
            self.completion = completion
            isRecording = true
            elapsedTime = 0
            timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                guard let self, let recorder = self.recorder else { return }
                self.elapsedTime = recorder.currentTime
            }
        } catch {
            onDenied("Unable to start recording: \(error.localizedDescription)")
        }
    }

    func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        let url = recordingURL
        let duration = recorder.currentTime
        let callback = completion
        reset()
        guard flag, let url else {
            if let url { try? FileManager.default.removeItem(at: url) }
            return
        }
        callback?(url, duration)
    }

    private func reset() {
        timer?.invalidate()
        timer = nil
        recorder = nil
        recordingURL = nil
        completion = nil
        isRecording = false
        elapsedTime = 0
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }
}

enum AnnotationStore {
    static func save(_ document: AnnotationDocument, to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(document)
        let temporaryURL = url.deletingLastPathComponent().appendingPathComponent(".annotations-\(UUID().uuidString).tmp")
        try data.write(to: temporaryURL, options: .completeFileProtectionUnlessOpen)
        if FileManager.default.fileExists(atPath: url.path) {
            _ = try FileManager.default.replaceItemAt(url, withItemAt: temporaryURL)
        } else {
            try FileManager.default.moveItem(at: temporaryURL, to: url)
        }
    }
}