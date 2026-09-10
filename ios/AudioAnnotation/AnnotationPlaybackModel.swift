import AVFoundation
import Foundation

@MainActor
final class AnnotationPlaybackModel: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var isPlaying = false

    private var player: AVAudioPlayer?
    private var queue: [URL] = []
    private var completion: (() -> Void)?

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
