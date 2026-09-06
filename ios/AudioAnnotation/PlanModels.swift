import Foundation

struct TimingManifest: Codable {
    let planID: String
    let audioFile: String
    let durationSeconds: Double
    let sentences: [Sentence]

    enum CodingKeys: String, CodingKey {
        case planID = "plan_id"
        case audioFile = "audio_file"
        case durationSeconds = "duration_seconds"
        case sentences
    }
}

struct Sentence: Codable, Identifiable {
    let sentenceID: String
    let index: Int
    let text: String
    let startSeconds: Double
    let endSeconds: Double

    var id: String { sentenceID }

    enum CodingKeys: String, CodingKey {
        case sentenceID = "sentence_id"
        case index
        case text
        case startSeconds = "start_seconds"
        case endSeconds = "end_seconds"
    }
}

struct AnnotationFile: Codable, Identifiable {
    let audioFile: String
    let recordedAt: String
    let durationSeconds: Double?
    let transcribedText: String?

    var id: String { audioFile }

    enum CodingKeys: String, CodingKey {
        case audioFile = "audio_file"
        case recordedAt = "recorded_at"
        case durationSeconds = "duration_seconds"
        case transcribedText = "transcribed_text"
    }

    init(audioFile: String, recordedAt: String, durationSeconds: Double?, transcribedText: String? = nil) {
        self.audioFile = audioFile
        self.recordedAt = recordedAt
        self.durationSeconds = durationSeconds
        self.transcribedText = transcribedText
    }
}

struct Annotation: Codable, Identifiable {
    let annotationID: String
    let sentenceID: String?
    let timestampSeconds: Double
    let annotationText: String?
    let audioFiles: [AnnotationFile]

    var id: String { annotationID }

    enum CodingKeys: String, CodingKey {
        case annotationID = "annotation_id"
        case sentenceID = "sentence_id"
        case timestampSeconds = "timestamp_seconds"
        case annotationText = "annotation_text"
        case audioFiles = "audio_files"
    }
}

struct AnnotationDocument: Codable {
    let schemaVersion: Int
    let planID: String?
    let audioGeneration: String?
    let manifestFile: String?
    var annotations: [Annotation]

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case planID = "plan_id"
        case audioGeneration = "audio_generation"
        case manifestFile = "manifest_file"
        case annotations
    }

    init(schemaVersion: Int = 1, planID: String? = nil, audioGeneration: String? = nil, manifestFile: String? = nil, annotations: [Annotation]) {
        self.schemaVersion = schemaVersion
        self.planID = planID
        self.audioGeneration = audioGeneration
        self.manifestFile = manifestFile
        self.annotations = annotations
    }
}
