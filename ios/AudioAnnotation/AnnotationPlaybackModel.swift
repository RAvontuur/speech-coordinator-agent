import AVFoundation
import Foundation

@MainActor
final class AnnotationPlaybackModel: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var isPlaying = false

    private var player: AVAudioPlayer?
    private var queue: [URL] = []
    private var completion: (() -> Void)?
    private var sessionObservers: [NSObjectProtocol] = []

    override init() {
        super.init()
        let notificationCenter = NotificationCenter.default
        let session = AVAudioSession.sharedInstance()
        sessionObservers = [
            notificationCenter.addObserver(
                forName: AVAudioSession.interruptionNotification,
                object: session,
                queue: .main
            ) { [weak self] notification in
                guard
                    let rawType = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                    AVAudioSession.InterruptionType(rawValue: rawType) == .began
                else {
                    return
                }
                Task { @MainActor in self?.pause() }
            },
            notificationCenter.addObserver(
                forName: AVAudioSession.routeChangeNotification,
                object: session,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.pause() }
            }
        ]
    }

    deinit {
        sessionObservers.forEach(NotificationCenter.default.removeObserver)
    }

    func play(urls: [URL], completion: (() -> Void)? = nil) throws {
        stop()
        let playableURLs = urls.filter { FileManager.default.fileExists(atPath: $0.path) }
        guard !playableURLs.isEmpty else {
            throw PlaybackError.noAudioFiles
        }
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playback, mode: .spokenAudio)
        try session.setActive(true)
        queue = playableURLs
        self.completion = completion
        playNext()
    }

    func stop() {
        player?.stop()
        player = nil
        queue.removeAll()
        completion = nil
        isPlaying = false
    }

    private func pause() {
        player?.pause()
        isPlaying = false
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        guard flag else {
            stop()
            return
        }
        playNext()
    }

    private func playNext() {
        guard !queue.isEmpty else {
            player = nil
            isPlaying = false
            let finished = completion
            completion = nil
            finished?()
            return
        }
        let url = queue.removeFirst()
        do {
            let nextPlayer = try AVAudioPlayer(contentsOf: url)
            nextPlayer.delegate = self
            nextPlayer.prepareToPlay()
            player = nextPlayer
            isPlaying = nextPlayer.play()
        } catch {
            stop()
        }
    }

    enum PlaybackError: LocalizedError {
        case noAudioFiles

        var errorDescription: String? {
            "No playable annotation audio files were found."
        }
    }
}
