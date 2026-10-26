#include <gtest/gtest.h>

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
#include <cmath>

#include "audio/types.h"
#include "track/beats.h"
#include "track/trackstructure.h"

using namespace mixxx;

namespace {

constexpr auto kSampleRate = audio::SampleRate(44100);
constexpr double kBpm = 128.0;
constexpr double kBeat = 60.0 / kBpm;
// The real first downbeat; the analyzer and the grid see it slightly
// differently (decoder offsets), which alignment must tolerate.
constexpr double kFirstDownbeat = 1.37;

/// Analyzer output for 64 bars: Intro (16) Build (8) Drop (16) Breakdown (24)
QByteArray makeJson(double analyzerOffset = 0.012) {
    QJsonArray beats;
    QJsonArray downbeats;
    for (int i = 0; i < 64 * 4; ++i) {
        const double t = kFirstDownbeat + analyzerOffset + i * kBeat;
        beats.append(t);
        if (i % 4 == 0) {
            downbeats.append(t);
        }
    }
    // The tracker misses a couple of downbeats and adds a wrong one
    downbeats.removeAt(10);
    downbeats.removeAt(20);
    downbeats.append(kFirstDownbeat + analyzerOffset + 130 * kBeat);

    const auto barTime = [&](int bar) {
        return kFirstDownbeat + analyzerOffset + bar * 4 * kBeat;
    };
    QJsonArray phrases;
    for (int bar = 0; bar < 64; bar += 8) {
        phrases.append(barTime(bar));
    }
    QJsonArray sections;
    const auto addSection = [&](int startBar, int endBar, const QString& label,
                                    const QString& color) {
        QJsonObject s;
        s.insert("start", barTime(startBar));
        s.insert("end", barTime(endBar));
        s.insert("label", label);
        s.insert("color", color);
        s.insert("energy", 0.5);
        sections.append(s);
    };
    addSection(0, 16, "Intro", "#3F8EFC");
    addSection(16, 24, "Build", "#F5B700");
    addSection(24, 40, "Drop", "#FF3B30");
    addSection(40, 64, "Breakdown", "#8E5CFF");

    QJsonArray cues;
    QJsonObject cue;
    cue.insert("position", barTime(24));
    cue.insert("label", "DROP");
    cue.insert("color", "#FF3B30");
    cues.append(cue);

    QJsonObject root;
    root.insert("format", "mixxx-structure");
    root.insert("version", 1);
    root.insert("bpm", kBpm);
    root.insert("beats_per_bar", 4);
    root.insert("phrase_bars", 8);
    root.insert("beats", beats);
    root.insert("downbeats", downbeats);
    root.insert("phrases", phrases);
    root.insert("sections", sections);
    root.insert("cues", cues);
    return QJsonDocument(root).toJson();
}

/// A grid whose first marker sits two beats *before* the real first
/// downbeat, so the bar phase is not simply "index % 4 == 0".
BeatsPointer makeGrid(double bpm) {
    const double firstMarkerSeconds = kFirstDownbeat - 2 * kBeat;
    return Beats::fromConstTempo(kSampleRate,
            audio::FramePos(std::round(firstMarkerSeconds * kSampleRate.toDouble())),
            Bpm(bpm));
}

int beatIndexAtSeconds(const Beats& beats, double seconds) {
    const auto index = TrackStructure::closestBeatIndex(beats, seconds);
    EXPECT_TRUE(index.has_value());
    return index.value_or(0);
}

} // namespace

TEST(TrackStructureTest, ParsesJson) {
    QString error;
    auto pStructure = TrackStructure::fromJson(makeJson(), &error);
    ASSERT_TRUE(pStructure) << error.toStdString();
    EXPECT_DOUBLE_EQ(kBpm, pStructure->bpm());
    EXPECT_EQ(4, pStructure->beatsPerBar());
    EXPECT_EQ(4, pStructure->sections().size());
    EXPECT_EQ(QStringLiteral("Drop"), pStructure->sections().at(2).label);
    EXPECT_EQ(QColor("#FF3B30"), pStructure->sections().at(2).color);
    EXPECT_EQ(1, pStructure->cueSuggestions().size());
    EXPECT_FALSE(pStructure->cuesApplied());
}

TEST(TrackStructureTest, RejectsOtherJson) {
    EXPECT_FALSE(TrackStructure::fromJson("{\"format\":\"something\",\"version\":1}"));
    EXPECT_FALSE(TrackStructure::fromJson("not json"));
}

TEST(TrackStructureTest, AlignsBarsAndPhrasesToGrid) {
    auto pStructure = TrackStructure::fromJson(makeJson());
    ASSERT_TRUE(pStructure);
    auto pBeats = makeGrid(kBpm);
    auto pAlignment = pStructure->alignTo(pBeats);
    ASSERT_TRUE(pAlignment);
    EXPECT_EQ(4, pAlignment->beatsPerBar);
    EXPECT_GT(pAlignment->confidence, 0.9);

    // The grid's first marker is 2 beats before the first downbeat.
    const int firstDownbeat = beatIndexAtSeconds(*pBeats, kFirstDownbeat);
    EXPECT_EQ(2, firstDownbeat);
    EXPECT_TRUE(pAlignment->isBarStart(firstDownbeat));
    EXPECT_TRUE(pAlignment->isBarStart(firstDownbeat + 4));
    EXPECT_TRUE(pAlignment->isBarStart(firstDownbeat - 4));
    EXPECT_FALSE(pAlignment->isBarStart(firstDownbeat + 1));
    EXPECT_FALSE(pAlignment->isBarStart(0));

    // Phrases every 8 bars
    EXPECT_TRUE(pAlignment->isPhraseStart(firstDownbeat));
    EXPECT_TRUE(pAlignment->isPhraseStart(firstDownbeat + 32));
    EXPECT_FALSE(pAlignment->isPhraseStart(firstDownbeat + 16));

    // Sections in beats
    ASSERT_EQ(4, pAlignment->sections.size());
    EXPECT_EQ(firstDownbeat + 24 * 4, pAlignment->sections.at(2).startBeat);
    EXPECT_EQ(firstDownbeat + 40 * 4, pAlignment->sections.at(2).endBeat);
    const auto* pSection = pAlignment->sectionAt(firstDownbeat + 24 * 4 + 5);
    ASSERT_TRUE(pSection);
    EXPECT_EQ(QStringLiteral("Drop"), pSection->label);

    // Cached for the same grid
    EXPECT_EQ(pAlignment, pStructure->alignTo(pBeats));

    // Helpers used by the controls
    EXPECT_EQ(firstDownbeat + 4, pAlignment->barStartAtOrBefore(firstDownbeat + 7));
    EXPECT_EQ(firstDownbeat + 8, pAlignment->snapToBar(firstDownbeat + 7));
    const auto pos = TrackStructure::beatPosition(*pBeats, firstDownbeat);
    EXPECT_EQ(firstDownbeat, TrackStructure::beatIndexAtOrBefore(*pBeats, pos));
    EXPECT_EQ(firstDownbeat, TrackStructure::beatIndexAtOrBefore(*pBeats, pos + 100));
}

TEST(TrackStructureTest, HandlesDoubleTempoGrid) {
    auto pStructure = TrackStructure::fromJson(makeJson());
    ASSERT_TRUE(pStructure);
    // Mixxx detected 256 BPM: a bar is 8 grid beats.
    auto pBeats = makeGrid(kBpm * 2);
    auto pAlignment = pStructure->computeAlignment(*pBeats);
    EXPECT_EQ(8, pAlignment->beatsPerBar);
    EXPECT_EQ(64, pAlignment->phraseBeats); // 8 bars of 8 grid beats
    EXPECT_GT(pAlignment->confidence, 0.9);
    const int firstDownbeat = beatIndexAtSeconds(*pBeats, kFirstDownbeat);
    EXPECT_TRUE(pAlignment->isBarStart(firstDownbeat));
    EXPECT_TRUE(pAlignment->isBarStart(firstDownbeat + 8));
    EXPECT_FALSE(pAlignment->isBarStart(firstDownbeat + 4));
}

TEST(TrackStructureTest, SidecarRoundTrip) {
    QTemporaryDir dir;
    ASSERT_TRUE(dir.isValid());
    const QString track = dir.filePath("Artist - Song.stem.mp4");
    EXPECT_FALSE(TrackStructure::fromSidecar(track));

    QFile file(TrackStructure::sidecarPath(track));
    ASSERT_TRUE(file.open(QIODevice::WriteOnly));
    file.write(makeJson());
    file.close();

    auto pStructure = TrackStructure::fromSidecar(track);
    ASSERT_TRUE(pStructure);
    EXPECT_FALSE(pStructure->cuesApplied());
    EXPECT_TRUE(TrackStructure::markCuesApplied(track));
    pStructure = TrackStructure::fromSidecar(track);
    ASSERT_TRUE(pStructure);
    EXPECT_TRUE(pStructure->cuesApplied());
    EXPECT_EQ(4, pStructure->sections().size());
}

TEST(TrackStructureTest, BarAndPhrasePositions) {
    TrackStructure::Alignment a;
    a.beatsPerBar = 4;
    a.phraseBeats = 32;
    a.barPhase = 1;
    // phrases every 8 bars from beat 1, plus a section starting mid-phrase
    a.phraseStartBeats = {1, 33, 65, 81};

    EXPECT_EQ(1, a.beatInBar(1));
    EXPECT_EQ(4, a.beatInBar(4));
    EXPECT_EQ(1, a.beatInBar(5));
    EXPECT_EQ(4, a.beatInBar(0));
    EXPECT_EQ(4, a.beatsUntilBar(1));
    EXPECT_EQ(1, a.beatsUntilBar(4));

    EXPECT_EQ(33, a.phraseStartAtOrBefore(40));
    EXPECT_EQ(65, a.phraseStartAtOrBefore(80));
    EXPECT_EQ(81, a.phraseStartAtOrBefore(85));
    EXPECT_EQ(81, a.phraseStartAtOrBefore(100));
    EXPECT_EQ(-31, a.phraseStartAtOrBefore(0)); // before the first phrase
    EXPECT_EQ(7, a.positionInPhrase(40));
    EXPECT_EQ(33, a.nextPhraseStart(1));
    EXPECT_EQ(81, a.nextPhraseStart(70));
    EXPECT_EQ(113, a.nextPhraseStart(100)); // after the last: whole phrases on

    // Without phrase data: phrases counted from the bar phase
    TrackStructure::Alignment noPhrases = a;
    noPhrases.phraseStartBeats.clear();
    EXPECT_EQ(33, noPhrases.phraseStartAtOrBefore(40));
    EXPECT_EQ(65, noPhrases.nextPhraseStart(40));

    // Smallest move to line up phrase positions
    EXPECT_EQ(-4, TrackStructure::Alignment::syncDelta(5, 1, 32));
    EXPECT_EQ(4, TrackStructure::Alignment::syncDelta(30, 2, 32));
    EXPECT_EQ(16, TrackStructure::Alignment::syncDelta(0, 16, 32));
    EXPECT_EQ(0, TrackStructure::Alignment::syncDelta(3, 3, 32));
    EXPECT_EQ(-1, TrackStructure::Alignment::syncDelta(2, 1, 4)); // bars only
}

TEST(TrackStructureTest, Tier) {
    auto pStructure = TrackStructure::fromJson(makeJson());
    ASSERT_TRUE(pStructure);
    EXPECT_TRUE(pStructure->analyzedFromStems()); // files without a tier
    QJsonObject root = QJsonDocument::fromJson(makeJson()).object();
    root.insert("tier", "mix");
    pStructure = TrackStructure::fromJson(QJsonDocument(root).toJson());
    ASSERT_TRUE(pStructure);
    EXPECT_FALSE(pStructure->analyzedFromStems());
}

TEST(TrackStructureTest, StemCache) {
    QTemporaryDir dir;
    ASSERT_TRUE(dir.isValid());
    const auto writeFile = [](const QString& path, const QByteArray& data) {
        QFile file(path);
        ASSERT_TRUE(file.open(QIODevice::WriteOnly));
        file.write(data);
    };
    const QString track = dir.filePath("Artist - Song.mp3");
    const QString stems = dir.filePath("Artist - Song.stem.mp4");
    writeFile(track, QByteArray(1000, 'x'));
    writeFile(stems, QByteArray(10, 'y'));
    const auto writeSidecar = [&](const QJsonObject& extra) {
        QJsonObject root = QJsonDocument::fromJson(makeJson()).object();
        root.insert("stems", stems);
        root.insert("source_size", 1000);
        root.insert("stems_offset_ms", 0.4);
        root.insert("stems_sample_rate", 44100);
        for (auto it = extra.begin(); it != extra.end(); ++it) {
            root.insert(it.key(), it.value());
        }
        writeFile(TrackStructure::sidecarPath(track), QJsonDocument(root).toJson());
    };
    const auto sampleRate = audio::SampleRate(44100);

    EXPECT_TRUE(TrackStructure::stemCacheFor(track, sampleRate).isEmpty()); // no sidecar

    writeSidecar({});
    EXPECT_EQ(stems, TrackStructure::stemCacheFor(track, sampleRate));

    // Beats and cues are in frames: the sample rate must match
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, audio::SampleRate(48000)).isEmpty());
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, audio::SampleRate()).isEmpty());

    // Out of sync
    writeSidecar({{"stems_offset_ms", -12.0}});
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, sampleRate).isEmpty());
    writeSidecar({{"stems_offset_ms", QJsonValue()}});
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, sampleRate).isEmpty());

    // Made from an older version of the file
    writeSidecar({{"source_size", 999}});
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, sampleRate).isEmpty());

    // Stem file deleted
    writeSidecar({});
    ASSERT_TRUE(QFile::remove(stems));
    EXPECT_TRUE(TrackStructure::stemCacheFor(track, sampleRate).isEmpty());

    // A stem file's own sidecar points at itself: nothing to substitute
    writeFile(stems, QByteArray(10, 'y'));
    writeFile(TrackStructure::sidecarPath(stems),
            QJsonDocument::fromJson(QStringLiteral("{\"stems\": \"%1\"}")
                                            .arg(stems)
                                            .toUtf8())
                    .toJson());
    EXPECT_TRUE(TrackStructure::stemCacheFor(stems, sampleRate).isEmpty());
}
