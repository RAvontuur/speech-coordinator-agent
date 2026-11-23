import AVFoundation
import Foundation

@MainActor
final class AnnotationRecorder: NSObject, ObservableObject, AVAudioRecorderDelegate {
    @Published private(set) var isRecording = false
    @Published private(set) var elapsedTime = 0.0

    private var recorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var completedRecordingURL: URL?
    private var timer: Timer?
    private var completion: ((URL, Double) -> Void)?
    private var onError: ((String) -> Void)?

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
            try? FileManager.default.removeItem(at: recordingURL.deletingLastPathComponent())
        }
        reset()
    }

    private func start(in folder: URL, completion: @escaping (URL, Double) -> Void, onDenied: @escaping (String) -> Void) {
        let recordingID = UUID().uuidString
        let audioFolder = folder.appendingPathComponent("audio", isDirectory: true)
        let stagingFolder = audioFolder.appendingPathComponent(".recording-\(recordingID)", isDirectory: true)
        let stagingURL = stagingFolder.appendingPathComponent("annotation-\(recordingID).m4a")
        let completedURL = audioFolder.appendingPathComponent("annotation-\(recordingID).m4a")
        do {
            try FileManager.default.createDirectory(at: audioFolder, withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: stagingFolder, withIntermediateDirectories: true)
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)
            let recorder = try AVAudioRecorder(url: stagingURL, settings: [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 44_100,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ])
            recorder.delegate = self
            recorder.prepareToRecord()
            guard recorder.record() else {
                try? FileManager.default.removeItem(at: stagingFolder)
                onDenied("The microphone could not start recording.")
                return
            }
            self.recorder = recorder
            recordingURL = stagingURL
            completedRecordingURL = completedURL
            self.completion = completion
            onError = onDenied
            isRecording = true
            elapsedTime = 0
            timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                guard let self, let recorder = self.recorder else { return }
                self.elapsedTime = recorder.currentTime
            }
        } catch {
            try? FileManager.default.removeItem(at: stagingFolder)
            onDenied("Unable to start recording: \(error.localizedDescription)")
        }
    }

    func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        let stagingURL = recordingURL
        let completedURL = completedRecordingURL
        let duration = recorder.currentTime
        let callback = completion
        let errorCallback = onError
        reset()
        guard flag, let stagingURL, let completedURL else {
            if let stagingURL {
                try? FileManager.default.removeItem(at: stagingURL.deletingLastPathComponent())
            }
            if !flag {
                errorCallback?("The annotation recording did not finish successfully.")
            }
            return
        }
        do {
            try FileManager.default.moveItem(at: stagingURL, to: completedURL)
        } catch {
            try? FileManager.default.removeItem(at: stagingURL.deletingLastPathComponent())
            errorCallback?("Unable to finalize annotation recording: \(error.localizedDescription)")
            return
        }
        try? FileManager.default.removeItem(at: stagingURL.deletingLastPathComponent())
        callback?(completedURL, duration)
    }

    private func reset() {
        timer?.invalidate()
        timer = nil
        recorder = nil
        recordingURL = nil
        completedRecordingURL = nil
        completion = nil
        onError = nil
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