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

struct AnnotationFile: Codable {
    let audioFile: String
    let recordedAt: String
    let durationSeconds: Double?

    enum CodingKeys: String, CodingKey {
        case audioFile = "audio_file"
        case recordedAt = "recorded_at"
        case durationSeconds = "duration_seconds"
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
    let annotations: [Annotation]
}
