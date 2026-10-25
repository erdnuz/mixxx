#include "track/trackstructure.h"

#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <algorithm>
#include <cmath>

#include "util/logger.h"

namespace mixxx {

namespace {

const Logger kLogger("TrackStructure");

const QString kSidecarSuffix = QStringLiteral(".structure.json");
const QString kFormatName = QStringLiteral("mixxx-structure");
constexpr int kSupportedVersion = 1;
// Sidecars are small (a few hundred KB at most); refuse anything silly.
constexpr qint64 kMaxSidecarBytes = 16 * 1024 * 1024;

QVector<double> toDoubleVector(const QJsonValue& value) {
    QVector<double> result;
    const QJsonArray array = value.toArray();
    result.reserve(array.size());
    for (const auto& v : array) {
        if (v.isDouble()) {
            result.append(v.toDouble());
        }
    }
    std::sort(result.begin(), result.end());
    return result;
}

double median(QVector<double> values) {
    if (values.isEmpty()) {
        return 0;
    }
    const auto mid = values.begin() + values.size() / 2;
    std::nth_element(values.begin(), mid, values.end());
    return *mid;
}

} // namespace

// static
std::optional<int> TrackStructure::closestBeatIndex(const Beats& beats, double seconds) {
    const double sampleRate = beats.getSampleRate().toDouble();
    if (sampleRate <= 0 || !std::isfinite(seconds)) {
        return std::nullopt;
    }
    const auto position = audio::FramePos(std::round(seconds * sampleRate));
    auto it = beats.iteratorFrom(position);
    auto prev = std::prev(it);
    const double distNext = std::abs(*it - position);
    const double distPrev = std::abs(*prev - position);
    auto closest = distPrev <= distNext ? prev : it;
    const double dist = std::min(distPrev, distNext);
    const double beatLength = closest.beatLengthFrames();
    if (beatLength <= 0 || dist > beatLength * 0.5) {
        return std::nullopt;
    }
    return closest - beats.cfirstmarker();
}

// static
audio::FramePos TrackStructure::beatPosition(const Beats& beats, int beatIndex) {
    auto it = beats.cfirstmarker();
    it += beatIndex;
    return *it;
}

// static
int TrackStructure::beatIndexAtOrBefore(const Beats& beats, audio::FramePos position) {
    auto it = beats.iteratorFrom(position);
    if (*it > position) {
        it = std::prev(it);
    }
    return it - beats.cfirstmarker();
}

const TrackStructure::Alignment::SectionSpan* TrackStructure::Alignment::sectionAt(
        int beatIndex) const {
    for (const auto& section : sections) {
        if (beatIndex >= section.startBeat && beatIndex < section.endBeat) {
            return &section;
        }
    }
    return nullptr;
}

QList<int> TrackStructure::Alignment::sortedPhraseStarts() const {
    QList<int> result(phraseStartBeats.begin(), phraseStartBeats.end());
    std::sort(result.begin(), result.end());
    return result;
}

// static
QString TrackStructure::sidecarPath(const QString& trackLocation) {
    return trackLocation + kSidecarSuffix;
}

// static
TrackStructurePointer TrackStructure::fromSidecar(const QString& trackLocation) {
    if (trackLocation.isEmpty()) {
        return nullptr;
    }
    const QString path = sidecarPath(trackLocation);
    QFile file(path);
    if (!file.exists()) {
        return nullptr;
    }
    if (file.size() > kMaxSidecarBytes) {
        kLogger.warning() << "Ignoring oversized structure file" << path;
        return nullptr;
    }
    if (!file.open(QIODevice::ReadOnly)) {
        kLogger.warning() << "Failed to open" << path;
        return nullptr;
    }
    QString error;
    auto pStructure = fromJson(file.readAll(), &error);
    if (!pStructure) {
        kLogger.warning() << "Invalid structure file" << path << error;
        return nullptr;
    }
    kLogger.info() << "Loaded" << pStructure->sections().size() << "sections for"
                   << QFileInfo(trackLocation).fileName();
    return pStructure;
}

// static
TrackStructurePointer TrackStructure::fromJson(const QByteArray& json, QString* pError) {
    QJsonParseError parseError;
    const QJsonDocument doc = QJsonDocument::fromJson(json, &parseError);
    if (doc.isNull() || !doc.isObject()) {
        if (pError) {
            *pError = parseError.errorString();
        }
        return nullptr;
    }
    const QJsonObject root = doc.object();
    if (root.value(QStringLiteral("format")).toString() != kFormatName) {
        if (pError) {
            *pError = QStringLiteral("not a mixxx-structure file");
        }
        return nullptr;
    }
    const int version = root.value(QStringLiteral("version")).toInt(-1);
    if (version <= 0) {
        if (pError) {
            *pError = QStringLiteral("missing version");
        }
        return nullptr;
    }
    if (version > kSupportedVersion) {
        kLogger.warning() << "Structure file version" << version
                          << "is newer than supported; trying anyway";
    }

    auto pStructure = std::make_shared<TrackStructure>();
    pStructure->m_bpm = root.value(QStringLiteral("bpm")).toDouble(0);
    pStructure->m_beatsPerBar = std::clamp(
            root.value(QStringLiteral("beats_per_bar")).toInt(4), 1, 16);
    pStructure->m_phraseBars = std::clamp(
            root.value(QStringLiteral("phrase_bars")).toInt(8), 1, 64);
    pStructure->m_beats = toDoubleVector(root.value(QStringLiteral("beats")));
    pStructure->m_downbeats = toDoubleVector(root.value(QStringLiteral("downbeats")));
    pStructure->m_phrases = toDoubleVector(root.value(QStringLiteral("phrases")));
    pStructure->m_cuesApplied = root.value(QStringLiteral("mixxx_cues_applied")).toBool(false);

    const QJsonArray sections = root.value(QStringLiteral("sections")).toArray();
    for (const auto& value : sections) {
        const QJsonObject obj = value.toObject();
        Section section;
        section.startSeconds = obj.value(QStringLiteral("start")).toDouble(-1);
        section.endSeconds = obj.value(QStringLiteral("end")).toDouble(-1);
        section.label = obj.value(QStringLiteral("label")).toString();
        section.color = QColor(obj.value(QStringLiteral("color")).toString());
        if (!section.color.isValid()) {
            section.color = QColor(Qt::white);
        }
        section.energy = obj.value(QStringLiteral("energy")).toDouble(0);
        if (section.startSeconds < 0 || section.endSeconds <= section.startSeconds) {
            continue;
        }
        pStructure->m_sections.append(section);
    }
    std::sort(pStructure->m_sections.begin(),
            pStructure->m_sections.end(),
            [](const Section& a, const Section& b) {
                return a.startSeconds < b.startSeconds;
            });

    const QJsonArray cues = root.value(QStringLiteral("cues")).toArray();
    for (const auto& value : cues) {
        const QJsonObject obj = value.toObject();
        CueSuggestion cue;
        cue.positionSeconds = obj.value(QStringLiteral("position")).toDouble(-1);
        cue.label = obj.value(QStringLiteral("label")).toString();
        cue.color = QColor(obj.value(QStringLiteral("color")).toString());
        if (cue.positionSeconds < 0) {
            continue;
        }
        pStructure->m_cues.append(cue);
    }

    if (pStructure->m_downbeats.isEmpty() && pStructure->m_sections.isEmpty()) {
        if (pError) {
            *pError = QStringLiteral("no downbeats or sections");
        }
        return nullptr;
    }
    return pStructure;
}

// static
bool TrackStructure::markCuesApplied(const QString& trackLocation) {
    const QString path = sidecarPath(trackLocation);
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        return false;
    }
    QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
    file.close();
    if (!doc.isObject()) {
        return false;
    }
    QJsonObject root = doc.object();
    root.insert(QStringLiteral("mixxx_cues_applied"), true);
    QSaveFile out(path);
    if (!out.open(QIODevice::WriteOnly)) {
        kLogger.warning() << "Cannot write" << path;
        return false;
    }
    out.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
    return out.commit();
}

std::shared_ptr<const TrackStructure::Alignment> TrackStructure::alignTo(
        const BeatsPointer& pBeats) const {
    if (!pBeats) {
        return nullptr;
    }
    std::lock_guard<std::mutex> lock(m_alignmentMutex);
    if (m_pAlignment && m_pAlignedBeats == pBeats) {
        return m_pAlignment;
    }
    m_pAlignment = computeAlignment(*pBeats);
    m_pAlignedBeats = pBeats;
    return m_pAlignment;
}

std::shared_ptr<TrackStructure::Alignment> TrackStructure::computeAlignment(
        const Beats& beats) const {
    auto pAlignment = std::make_shared<Alignment>();
    const double sampleRate = beats.getSampleRate().toDouble();
    if (sampleRate <= 0) {
        return pAlignment;
    }

    // Mixxx may have detected the track at double or half the tempo the
    // analyzer found. Convert "beats per bar" into grid beats.
    int gridBeatsPerBar = m_beatsPerBar;
    QVector<double> intervals;
    for (int i = 1; i < m_beats.size(); ++i) {
        intervals.append(m_beats[i] - m_beats[i - 1]);
    }
    const double analyzerBeatSeconds = median(intervals);
    if (analyzerBeatSeconds > 0) {
        const double middle = m_beats.isEmpty() ? 0 : m_beats[m_beats.size() / 2];
        auto it = beats.iteratorFrom(audio::FramePos(std::round(middle * sampleRate)));
        const double gridBeatSeconds = it.beatLengthFrames() / sampleRate;
        if (gridBeatSeconds > 0) {
            const double ratio = analyzerBeatSeconds / gridBeatSeconds;
            if (ratio > 1.6 && ratio < 2.4) {
                gridBeatsPerBar = m_beatsPerBar * 2;
            } else if (ratio > 0.4 && ratio < 0.6 && m_beatsPerBar % 2 == 0) {
                gridBeatsPerBar = m_beatsPerBar / 2;
            }
        }
    }
    pAlignment->beatsPerBar = std::max(1, gridBeatsPerBar);
    const int bpb = pAlignment->beatsPerBar;

    // Bar phase: majority vote of the detected downbeats.
    QVector<int> votes(bpb, 0);
    int total = 0;
    for (double seconds : m_downbeats) {
        const auto index = closestBeatIndex(beats, seconds);
        if (index) {
            votes[Alignment::floorMod(*index, bpb)]++;
            total++;
        }
    }
    if (total > 0) {
        const auto best = std::max_element(votes.begin(), votes.end());
        pAlignment->barPhase = static_cast<int>(best - votes.begin());
        pAlignment->confidence = static_cast<double>(*best) / total;
    }

    const auto snapToBar = [&](int index) {
        return pAlignment->snapToBar(index);
    };

    for (double seconds : m_phrases) {
        const auto index = closestBeatIndex(beats, seconds);
        if (index) {
            pAlignment->phraseStartBeats.insert(snapToBar(*index));
        }
    }

    for (const auto& section : m_sections) {
        const auto start = closestBeatIndex(beats, section.startSeconds);
        if (!start) {
            continue;
        }
        Alignment::SectionSpan span;
        span.startBeat = snapToBar(*start);
        const auto end = closestBeatIndex(beats, section.endSeconds);
        span.endBeat = end ? snapToBar(*end) : span.startBeat + bpb;
        span.label = section.label;
        span.color = section.color;
        // Make sections contiguous and non-overlapping after snapping.
        if (!pAlignment->sections.isEmpty()) {
            auto& previous = pAlignment->sections.last();
            if (span.startBeat <= previous.startBeat) {
                continue;
            }
            previous.endBeat = span.startBeat;
        }
        if (span.endBeat <= span.startBeat) {
            span.endBeat = span.startBeat + bpb;
        }
        pAlignment->sections.append(span);
        pAlignment->phraseStartBeats.insert(span.startBeat);
    }
    return pAlignment;
}

} // namespace mixxx
