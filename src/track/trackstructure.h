#pragma once

#include <QByteArray>
#include <QColor>
#include <QList>
#include <QSet>
#include <QString>
#include <QVector>
#include <memory>
#include <mutex>
#include <optional>

#include "track/beats.h"

namespace mixxx {

class TrackStructure;
using TrackStructurePointer = std::shared_ptr<const TrackStructure>;

/// Bars, phrases and sections (Intro, Build, Drop, Breakdown, ...) of a
/// track, detected by the external "stemprep" analyzer (beat/downbeat
/// tracking + stem energy) and stored next to the audio file as
/// "<file name>.structure.json".
///
/// The analyzer works in seconds on its own decode of the file. To be robust
/// against small decoder offsets and to stay in sync with the user's own
/// (possibly edited) beat grid, everything is snapped to the beats of
/// Mixxx's grid by alignTo(): downbeats become a bar phase, phrase and
/// section starts become beat indices on the grid.
class TrackStructure {
  public:
    struct Section {
        double startSeconds = 0;
        double endSeconds = 0;
        QString label;
        QColor color;
        double energy = 0;
    };

    struct CueSuggestion {
        double positionSeconds = 0;
        QString label;
        QColor color;
    };

    /// The structure expressed in beat indices of one particular beat grid.
    /// Beat indices are counted from Beats::cfirstmarker() (can be negative).
    struct Alignment {
        struct SectionSpan {
            int startBeat;
            int endBeat; // exclusive
            QString label;
            QColor color;
        };

        int beatsPerBar = 4;
        /// Grid beats in one phrase (phrase_bars bars).
        int phraseBeats = 32;
        /// Beat index i is the first beat of a bar if
        /// floorMod(i - barPhase, beatsPerBar) == 0.
        int barPhase = 0;
        /// Fraction of detected downbeats that agreed with barPhase (0..1).
        double confidence = 0;
        QSet<int> phraseStartBeats;
        QList<SectionSpan> sections;

        bool isBarStart(int beatIndex) const {
            return floorMod(beatIndex - barPhase, beatsPerBar) == 0;
        }
        bool isPhraseStart(int beatIndex) const {
            return phraseStartBeats.contains(beatIndex);
        }
        /// Section containing beatIndex, or nullptr.
        const SectionSpan* sectionAt(int beatIndex) const;
        /// Sorted list of phrase starts.
        QList<int> sortedPhraseStarts() const;
        /// Nearest beat index that starts a bar.
        int snapToBar(int beatIndex) const {
            const int d = floorMod(beatIndex - barPhase, beatsPerBar);
            return d <= beatsPerBar / 2 ? beatIndex - d : beatIndex + (beatsPerBar - d);
        }
        /// Start of the bar containing beatIndex.
        int barStartAtOrBefore(int beatIndex) const {
            return beatIndex - floorMod(beatIndex - barPhase, beatsPerBar);
        }
        /// 1-based beat in the bar.
        int beatInBar(int beatIndex) const {
            return floorMod(beatIndex - barPhase, beatsPerBar) + 1;
        }
        /// Whole beats from beatIndex to the next downbeat (1..beatsPerBar).
        int beatsUntilBar(int beatIndex) const {
            return beatsPerBar - floorMod(beatIndex - barPhase, beatsPerBar);
        }
        /// Start of the phrase containing beatIndex: the last phrase start at
        /// or before it, continued backwards in whole phrases before the
        /// first one; without phrase data, phrases counted from the bar phase.
        int phraseStartAtOrBefore(int beatIndex) const;
        /// Beats since the start of the current phrase (0..phraseBeats-1).
        int positionInPhrase(int beatIndex) const {
            return floorMod(beatIndex - phraseStartAtOrBefore(beatIndex), phraseBeats);
        }
        /// First phrase start after beatIndex.
        int nextPhraseStart(int beatIndex) const;

        /// Whole beats to move a deck whose position in its phrase (or bar)
        /// is `own` so that it matches `reference`; the smallest move, in
        /// (-period/2, period/2].
        static int syncDelta(int own, int reference, int period) {
            int delta = floorMod(reference - own, period);
            if (delta > period / 2) {
                delta -= period;
            }
            return delta;
        }

        static int floorMod(int a, int b) {
            const int m = a % b;
            return m < 0 ? m + b : m;
        }
    };

    /// "<location>.structure.json"
    static QString sidecarPath(const QString& trackLocation);
    /// Returns nullptr if there is no (valid) sidecar for this file.
    static TrackStructurePointer fromSidecar(const QString& trackLocation);
    static TrackStructurePointer fromJson(const QByteArray& json, QString* pError = nullptr);

    /// Index (relative to Beats::cfirstmarker()) of the grid beat closest to
    /// `seconds`, if one is within half a beat.
    static std::optional<int> closestBeatIndex(const Beats& beats, double seconds);
    /// Frame position of the grid beat with the given index.
    static audio::FramePos beatPosition(const Beats& beats, int beatIndex);
    /// Index of the last grid beat at or before `position` (can be the beat
    /// exactly at `position`).
    static int beatIndexAtOrBefore(const Beats& beats, audio::FramePos position);

    /// Remember in the sidecar that the suggested hot cues were added to the
    /// library once, so cues the user deletes don't come back.
    static bool markCuesApplied(const QString& trackLocation);

    /// The stem file stemprep made for this track ("stems" in the sidecar),
    /// to be decoded instead of the track's own file so it plays with stems.
    /// Empty unless the stem file exists, was made from this very file (same
    /// size), plays in sync with it (|stems_offset_ms| <= 5) and has the
    /// track's sample rate (beats and cues are stored in frames).
    static QString stemCacheFor(const QString& trackLocation, audio::SampleRate trackSampleRate);

    /// True if the sections were detected from separated stems ("tier":
    /// "stems"; files without a tier were always made from stems). Analyses
    /// from the full mix only ("tier": "mix") are rougher.
    bool analyzedFromStems() const {
        return m_fromStems;
    }

    double bpm() const {
        return m_bpm;
    }
    int beatsPerBar() const {
        return m_beatsPerBar;
    }
    int phraseBars() const {
        return m_phraseBars;
    }
    const QVector<double>& beatsSeconds() const {
        return m_beats;
    }
    const QVector<double>& downbeatsSeconds() const {
        return m_downbeats;
    }
    const QVector<double>& phrasesSeconds() const {
        return m_phrases;
    }
    const QList<Section>& sections() const {
        return m_sections;
    }
    const QList<CueSuggestion>& cueSuggestions() const {
        return m_cues;
    }
    bool cuesApplied() const {
        return m_cuesApplied;
    }

    /// Snap the structure to a beat grid. The result is cached for the last
    /// grid it was computed for, so this is cheap to call every frame.
    std::shared_ptr<const Alignment> alignTo(const BeatsPointer& pBeats) const;

    /// Same, without caching (used by tests and by alignTo()).
    std::shared_ptr<Alignment> computeAlignment(const Beats& beats) const;

  private:
    double m_bpm = 0;
    int m_beatsPerBar = 4;
    int m_phraseBars = 8;
    QVector<double> m_beats;
    QVector<double> m_downbeats;
    QVector<double> m_phrases;
    QList<Section> m_sections;
    QList<CueSuggestion> m_cues;
    bool m_cuesApplied = false;
    bool m_fromStems = true;

    mutable std::mutex m_alignmentMutex;
    mutable BeatsPointer m_pAlignedBeats;
    mutable std::shared_ptr<const Alignment> m_pAlignment;
};

} // namespace mixxx
