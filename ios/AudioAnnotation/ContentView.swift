import AVFoundation
import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var audioPlayer = AudioPlayerModel()
    @State private var manifest: TimingManifest?
    @State private var annotations: [Annotation] = []
    @State private var showingImporter = false
    @State private var selectedRate: Float = 1.0
    @State private var errorMessage: String?
    @State private var packageFolder: URL?
    @State private var annotationPlayer: AVAudioPlayer?

    var body: some View {
        NavigationStack {
            Group {
                if let manifest {
                    playerView(manifest)
                } else {
                    emptyState
                }
            }
            .navigationTitle("Audio Annotation")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Open Plan", systemImage: "folder") {
                        showingImporter = true
                    }
                }
            }
            .fileImporter(
                isPresented: $showingImporter,
                allowedContentTypes: [.folder],
                allowsMultipleSelection: false,
                onCompletion: importPackage
            )
            .alert("Unable to open plan", isPresented: .constant(errorMessage != nil)) {
                Button("OK") { errorMessage = nil }
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }

    private var emptyState: some View {
        ContentUnavailableView(
            "No plan loaded",
            systemImage: "waveform",
            description: Text("Open a shared plan package to begin playback.")
        )
    }

    private func playerView(_ manifest: TimingManifest) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text(currentSentence(in: manifest)?.text ?? "Ready to play")
                    .font(.title3.weight(.medium))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))

                VStack(spacing: 8) {
                    Slider(value: Binding(
                        get: { audioPlayer.currentTime },
                        set: { audioPlayer.seek(to: $0) }
                    ), in: 0...max(audioPlayer.duration, 1))
                    HStack {
                        Text(formatTime(audioPlayer.currentTime))
                        Spacer()
                        Text(formatTime(audioPlayer.duration))
                    }
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                }

                HStack(spacing: 24) {
                    Button("Back 10", systemImage: "gobackward.10") {
                        audioPlayer.seek(by: -10)
                    }
                    Button(action: audioPlayer.togglePlayback) {
                        Image(systemName: audioPlayer.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                            .font(.system(size: 48))
                    }
                    .accessibilityLabel(audioPlayer.isPlaying ? "Pause" : "Play")
                    Button("Forward 10", systemImage: "goforward.10") {
                        audioPlayer.seek(by: 10)
                    }
                }
                .frame(maxWidth: .infinity)

                Picker("Speech rate", selection: $selectedRate) {
                    Text("0.75x").tag(Float(0.75))
                    Text("1x").tag(Float(1.0))
                    Text("1.25x").tag(Float(1.25))
                    Text("1.5x").tag(Float(1.5))
                }
                .pickerStyle(.segmented)
                .onChange(of: selectedRate) { _, rate in audioPlayer.setRate(rate) }

                if !annotations.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Annotations")
                            .font(.headline)
                        ForEach(annotations) { annotation in
                            Button {
                                audioPlayer.seek(to: annotation.timestampSeconds)
                                playFirstRecording(of: annotation)
                            } label: {
                                HStack {
                                    Image(systemName: "waveform.circle")
                                    Text(formatTime(annotation.timestampSeconds))
                                    Spacer()
                                    Text(annotation.annotationText ?? "Annotation")
                                        .lineLimit(1)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
            }
            .padding()
        }
    }

    private func importPackage(result: Result<[URL], Error>) {
        do {
            guard let folder = try result.get().first else { return }
            folder.startAccessingSecurityScopedResource()
            packageFolder = folder
            let manifestURL = folder.appendingPathComponent("plan.timing.json")
            let annotationsURL = folder.appendingPathComponent("annotations.json")
            let manifestData = try Data(contentsOf: manifestURL)
            manifest = try JSONDecoder().decode(TimingManifest.self, from: manifestData)
            if let data = try? Data(contentsOf: annotationsURL) {
                annotations = (try? JSONDecoder().decode(AnnotationDocument.self, from: data))?.annotations ?? []
            }
            let audioURL = folder.appendingPathComponent(manifest?.audioFile ?? "plan.wav")
            try audioPlayer.load(url: audioURL)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func currentSentence(in manifest: TimingManifest) -> Sentence? {
        manifest.sentences.first { audioPlayer.currentTime >= $0.startSeconds && audioPlayer.currentTime < $0.endSeconds }
    }

    private func playFirstRecording(of annotation: Annotation) {
        guard let recording = annotation.audioFiles.first else { return }
        let url = packageFolder?.appendingPathComponent(recording.audioFile) ?? URL(fileURLWithPath: recording.audioFile)
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        annotationPlayer = try? AVAudioPlayer(contentsOf: url)
        annotationPlayer?.play()
    }

    private func formatTime(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "00:00" }
        return String(format: "%02d:%02d", Int(seconds) / 60, Int(seconds) % 60)
    }
}
