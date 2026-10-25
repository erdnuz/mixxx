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
