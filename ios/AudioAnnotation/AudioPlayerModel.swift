import AVFoundation
import Foundation

@MainActor
final class AudioPlayerModel: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var player: AVAudioPlayer?
    @Published private(set) var isPlaying = false
    @Published var currentTime = 0.0
    @Published private(set) var duration = 0.0

    private var timer: Timer?

    func load(url: URL) throws {
        stop()
        player = try AVAudioPlayer(contentsOf: url)
        player?.delegate = self
        player?.prepareToPlay()
        duration = player?.duration ?? 0
        currentTime = 0
    }

    func togglePlayback() {
        guard let player else { return }
        if player.isPlaying {
            player.pause()
            stopTimer()
        } else {
            player.play()
            startTimer()
        }
        isPlaying = player.isPlaying
    }

    func seek(by seconds: Double) {
        guard let player else { return }
        player.currentTime = min(max(player.currentTime + seconds, 0), player.duration)
        currentTime = player.currentTime
    }

    func seek(to seconds: Double) {
        guard let player else { return }
        player.currentTime = min(max(seconds, 0), player.duration)
        currentTime = player.currentTime
    }

    func setRate(_ rate: Float) {
        player?.enableRate = true
        player?.rate = rate
    }

    func stop() {
        player?.stop()
        player = nil
        isPlaying = false
        currentTime = 0
        duration = 0
        stopTimer()
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isPlaying = false
        currentTime = duration
        stopTimer()
    }

    private func startTimer() {
        stopTimer()
        timer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
            guard let self, let player = self.player else { return }
            self.currentTime = player.currentTime
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
}
