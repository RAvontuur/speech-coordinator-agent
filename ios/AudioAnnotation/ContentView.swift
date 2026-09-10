import AVFoundation
import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var audioPlayer = AudioPlayerModel()
    @StateObject private var annotationRecorder = AnnotationRecorder()
    @StateObject private var annotationPlayback = AnnotationPlaybackModel()
    @State private var manifest: TimingManifest?
    @State private var annotations: [Annotation] = []
    @State private var annotationDocument = AnnotationDocument(annotations: [])
    @State private var showingImporter = false
    @State private var selectedRate: Float = 1.0
    @State private var errorMessage: String?
    @State private var packageFolder: URL?
    @State private var selectedAnnotationID: String?
    @State private var recordingReply = false
    @State private var expandedAnnotationIDs: Set<String> = []

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
                    Button {
                        annotationPlayback.stop()
                        audioPlayer.togglePlayback()
                    } label: {
                        Image(systemName: audioPlayer.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                            .font(.system(size: 48))
                    }
                    .accessibilityLabel(audioPlayer.isPlaying ? "Pause" : "Play")
                    Button("Forward 10", systemImage: "goforward.10") {
                        audioPlayer.seek(by: 10)
                    }
                }
                .frame(maxWidth: .infinity)

                if annotationRecorder.isRecording {
                    recordingControls
                } else {
                    Button("Record annotation", systemImage: "mic.circle.fill") {
                        beginRecording(replyTo: nil)
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                }

                Picker("Speech rate", selection: $selectedRate) {
                    Text("0.75x").tag(Float(0.75))
                    Text("1x").tag(Float(1.0))
                    Text("1.25x").tag(Float(1.25))
                    Text("1.5x").tag(Float(1.5))
                }
                .pickerStyle(.segmented)
                .onChange(of: selectedRate) { _, rate in audioPlayer.setRate(rate) }

                annotationsView
            }
            .padding()
        }
    }

    @ViewBuilder
    private var annotationsView: some View {
        if !annotations.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Annotations")
                    .font(.headline)
                ForEach(Array(annotations.enumerated()), id: \.offset) { _, annotation in
                    annotationRow(annotation)
                }
            }
        }
    }

    private func annotationRow(_ annotation: Annotation) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                selectedAnnotationID = annotation.id
                playAnnotationThread(annotation)
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
            .simultaneousGesture(LongPressGesture(minimumDuration: 0.5).onEnded { _ in
                withAnimation {
                    _ = expandedAnnotationIDs.insert(annotation.id)
                }
            })

            if expandedAnnotationIDs.contains(annotation.id) {
                annotationThreadPanels(annotation)
            }
        }
    }

    @ViewBuilder
    private func annotationThreadPanels(_ annotation: Annotation) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(annotation.audioFiles.enumerated()), id: \.offset) { index, recording in
                Button {
                    playRecording(recording, in: annotation)
                } label: {
                    HStack {
                        Image(systemName: index == 0 ? "mic.circle" : "arrowshape.turn.up.left.circle")
                        Text(index == 0 ? "Original annotation" : "Reply \(index)")
                        Spacer()
                        if let duration = recording.durationSeconds {
                            Text(formatTime(duration))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.leading, 16)
                }
                .buttonStyle(.bordered)
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    Button(role: .destructive) {
                        removeRecording(recording, from: annotation)
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
            }

            if selectedAnnotationID == annotation.id && !annotationRecorder.isRecording {
                Button("Record reply", systemImage: "arrowshape.turn.up.left.circle") {
                    beginRecording(replyTo: annotation)
                }
                .font(.subheadline)
                .padding(.leading, 16)
            }
        }
        .padding(.vertical, 4)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 10))
    }

    private var recordingControls: some View {
        VStack(spacing: 10) {
            Label(recordingReply ? "Recording reply" : "Recording annotation", systemImage: "record.circle")
                .foregroundStyle(.red)
            Text(formatTime(annotationRecorder.elapsedTime))
                .font(.title2.monospacedDigit())
            HStack {
                Button("Cancel", role: .cancel) { annotationRecorder.cancel() }
                Button("Stop", systemImage: "stop.circle.fill") { annotationRecorder.stop() }
                    .buttonStyle(.borderedProminent)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(.red.opacity(0.1), in: RoundedRectangle(cornerRadius: 12))
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
                if let document = try? JSONDecoder().decode(AnnotationDocument.self, from: data) {
                    annotationDocument = document
                    annotations = document.annotations
                }
            }
            let audioURL = folder.appendingPathComponent(manifest?.audioFile ?? "plan.wav")
            try audioPlayer.load(url: audioURL)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func beginRecording(replyTo annotation: Annotation?) {
        guard let packageFolder else {
            errorMessage = "Open a plan package before recording."
            return
        }
        audioPlayer.pause()
        annotationPlayback.stop()
        recordingReply = annotation != nil
        annotationRecorder.requestPermissionAndStart(in: packageFolder, completion: { url, duration in
            saveRecording(url: url, duration: duration, replyTo: annotation)
        }, onDenied: { message in
            errorMessage = message
        })
    }

    private func saveRecording(url: URL, duration: Double, replyTo annotation: Annotation?) {
        guard let packageFolder, let manifest else { return }
        do {
            let file = AnnotationFile(
                audioFile: "audio/\(url.lastPathComponent)",
                recordedAt: ISO8601DateFormatter().string(from: Date()),
                durationSeconds: duration
            )
            if let annotation {
                guard let index = annotations.firstIndex(where: { $0.id == annotation.id }) else { return }
                annotations[index] = Annotation(
                    annotationID: annotation.annotationID,
                    sentenceID: annotation.sentenceID,
                    timestampSeconds: annotation.timestampSeconds,
                    annotationText: annotation.annotationText,
                    audioFiles: annotation.audioFiles + [file]
                )
            } else {
                let sentenceID = currentSentence(in: manifest)?.sentenceID
                let newAnnotation = Annotation(
                    annotationID: "a-\(UUID().uuidString)",
                    sentenceID: sentenceID,
                    timestampSeconds: audioPlayer.currentTime,
                    annotationText: nil,
                    audioFiles: [file]
                )
                annotations.append(newAnnotation)
                selectedAnnotationID = newAnnotation.id
            }
            annotationDocument = AnnotationDocument(
                schemaVersion: annotationDocument.schemaVersion,
                planID: annotationDocument.planID ?? manifest.planID,
                audioGeneration: annotationDocument.audioGeneration,
                manifestFile: annotationDocument.manifestFile ?? "plan.timing.json",
                annotations: annotations
            )
            try AnnotationStore.save(annotationDocument, to: packageFolder.appendingPathComponent("annotations.json"))
        } catch {
            try? FileManager.default.removeItem(at: url)
            errorMessage = "Unable to save annotation: \(error.localizedDescription)"
        }
    }

    private func currentSentence(in manifest: TimingManifest) -> Sentence? {
        manifest.sentences.first { audioPlayer.currentTime >= $0.startSeconds && audioPlayer.currentTime < $0.endSeconds }
    }

    private func playAnnotationThread(_ annotation: Annotation) {
        audioPlayer.seek(to: annotation.timestampSeconds)
        let urls = annotation.audioFiles.flatMap(annotationAudioURLs)
        do {
            try annotationPlayback.play(urls: urls) {
                audioPlayer.play()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func playRecording(_ recording: AnnotationFile, in annotation: Annotation) {
        do {
            try annotationPlayback.play(urls: annotationAudioURLs(recording))
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func annotationAudioURLs(_ recording: AnnotationFile) -> [URL] {
        let url = packageFolder?.appendingPathComponent(recording.audioFile) ?? URL(fileURLWithPath: recording.audioFile)
        var urls = [url]
        let sttURL = url.deletingPathExtension().appendingPathExtension("stt.wav")
        if FileManager.default.fileExists(atPath: sttURL.path) {
            urls.append(sttURL)
        }
        return urls
    }

    private func removeRecording(_ recording: AnnotationFile, from annotation: Annotation) {
        annotationPlayback.stop()
        guard let annotationIndex = annotations.firstIndex(where: { $0.id == annotation.id }) else { return }
        let remainingFiles = annotation.audioFiles.filter { $0.id != recording.id }
        annotations[annotationIndex] = Annotation(
            annotationID: annotation.annotationID,
            sentenceID: annotation.sentenceID,
            timestampSeconds: annotation.timestampSeconds,
            annotationText: annotation.annotationText,
            audioFiles: remainingFiles
        )
        if remainingFiles.isEmpty {
            annotations.remove(at: annotationIndex)
            expandedAnnotationIDs.remove(annotation.id)
            if selectedAnnotationID == annotation.id {
                selectedAnnotationID = nil
            }
        }
        guard let manifest, let packageFolder else { return }
        annotationDocument = AnnotationDocument(
            schemaVersion: annotationDocument.schemaVersion,
            planID: annotationDocument.planID ?? manifest.planID,
            audioGeneration: annotationDocument.audioGeneration,
            manifestFile: annotationDocument.manifestFile ?? "plan.timing.json",
            annotations: annotations
        )
        do {
            try AnnotationStore.save(annotationDocument, to: packageFolder.appendingPathComponent("annotations.json"))
            try? FileManager.default.removeItem(at: packageFolder.appendingPathComponent(recording.audioFile))
            let sttURL = packageFolder.appendingPathComponent(recording.audioFile).deletingPathExtension().appendingPathExtension("stt.wav")
            try? FileManager.default.removeItem(at: sttURL)
            let textURL = packageFolder.appendingPathComponent(recording.audioFile).deletingPathExtension().appendingPathExtension("stt.txt")
            try? FileManager.default.removeItem(at: textURL)
        } catch {
            errorMessage = "Unable to delete annotation: \(error.localizedDescription)"
        }
    }

    private func formatTime(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "00:00" }
        return String(format: "%02d:%02d", Int(seconds) / 60, Int(seconds) % 60)
    }
}
