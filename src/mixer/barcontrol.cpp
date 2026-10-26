#include "mixer/barcontrol.h"

#include <algorithm>
#include <cmath>

#include "control/controlobject.h"
#include "control/controlpushbutton.h"
#include "mixer/playerinfo.h"
#include "mixer/playermanager.h"
#include "moc_barcontrol.cpp"
#include "track/track.h"
#include "util/logger.h"
#ifdef __STEM__
#include "engine/channels/enginedeck.h"
#endif

namespace {

const mixxx::Logger kLogger("BarControl");

constexpr int kStatusIntervalMs = 25;
// Close enough to fire instead of waiting again
constexpr double kFireWindowMs = 15;
// Too late to make the next phrase reliably: take the one after
constexpr double kMinLeadMs = 150;

double get(const QString& group, const char* item) {
    return ControlObject::get(ConfigKey(group, QString::fromLatin1(item)));
}

void set(const QString& group, const char* item, double value) {
    ControlObject::set(ConfigKey(group, QString::fromLatin1(item)), value);
}

void trigger(const QString& group, const char* item) {
    set(group, item, 1);
    set(group, item, 0);
}

} // namespace

BarControl::BarControl(const QString& group, QObject* pParent)
        : QObject(pParent),
          m_group(group) {
    const auto readOnly = [&group](const char* item, double initial) {
        auto pControl = std::make_unique<ControlObject>(
                ConfigKey(group, QString::fromLatin1(item)));
        pControl->setReadOnly();
        pControl->forceSet(initial);
        return pControl;
    };
    m_pBeatInBar = readOnly("beat_in_bar", 0);
    m_pBeatsUntilBar = readOnly("beats_until_bar", 0);
    m_pBarInPhrase = readOnly("bar_in_phrase", 0);
    m_pStemMaskPending = readOnly("stem_mask_pending", -1);

    m_pPhraseSync = std::make_unique<ControlPushButton>(
            ConfigKey(group, QStringLiteral("phrase_sync")));
    connect(m_pPhraseSync.get(), &ControlObject::valueChanged, this, [this](double v) {
        if (v > 0) {
            phraseSync();
        }
    });
    m_pPlayOnPhrase = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("play_on_phrase")));
    connect(m_pPlayOnPhrase.get(), &ControlObject::valueChanged, this, [this](double v) {
        armPlayOnPhrase(v > 0);
    });
    // Request controls: handled, then set back to -1 / 0 so the same
    // request can be made again
    m_pStemMaskOnBar = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("stem_mask_on_bar")));
    m_pStemMaskOnBar->forceSet(-1);
    connect(m_pStemMaskOnBar.get(), &ControlObject::valueChanged, this, [this](double v) {
        if (v >= 0) {
            requestStemMask(static_cast<int>(v) & 0xF);
            m_pStemMaskOnBar->forceSet(-1);
        }
    });
    m_pBarLoop = std::make_unique<ControlObject>(ConfigKey(group, QStringLiteral("bar_loop")));
    connect(m_pBarLoop.get(), &ControlObject::valueChanged, this, [this](double v) {
        const int bars = static_cast<int>(v);
        if (bars <= 0) {
            return;
        }
        m_pBarLoop->forceSet(0);
        if (const auto pos = ownPosition()) {
            const auto& a = *pos->pAlignment;
            loopBeats(a.barStartAtOrBefore(pos->beat), bars * a.beatsPerBar);
        }
    });
    m_pPhraseLoop = std::make_unique<ControlPushButton>(
            ConfigKey(group, QStringLiteral("phrase_loop")));
    connect(m_pPhraseLoop.get(), &ControlObject::valueChanged, this, [this](double v) {
        if (v <= 0) {
            return;
        }
        if (const auto pos = ownPosition()) {
            const auto& a = *pos->pAlignment;
            loopBeats(a.phraseStartAtOrBefore(pos->beat), a.phraseBeats);
        }
    });
    m_pPhraseRestart = std::make_unique<ControlPushButton>(
            ConfigKey(group, QStringLiteral("phrase_restart")));
    connect(m_pPhraseRestart.get(), &ControlObject::valueChanged, this, [this](double v) {
        if (v <= 0) {
            return;
        }
        if (const auto pos = ownPosition()) {
            const auto& a = *pos->pAlignment;
            const int delta = a.phraseStartAtOrBefore(pos->beat) - a.barStartAtOrBefore(pos->beat);
            if (delta != 0) {
                set(m_group, "beatjump", delta);
            }
        }
    });

    for (QTimer* pTimer : {&m_stemTimer, &m_playTimer}) {
        pTimer->setSingleShot(true);
        pTimer->setTimerType(Qt::PreciseTimer);
    }
    connect(&m_stemTimer, &QTimer::timeout, this, &BarControl::stemMaskTimerFired);
    connect(&m_playTimer, &QTimer::timeout, this, &BarControl::firePlayOnPhrase);
    m_positionTimer.setInterval(kStatusIntervalMs);
    connect(&m_positionTimer, &QTimer::timeout, this, &BarControl::updateStatus);
}

BarControl::~BarControl() = default;

void BarControl::trackLoaded(TrackPointer pTrack) {
    m_pTrack = std::move(pTrack);
    m_stemTimer.stop();
    m_pStemMaskPending->forceSet(-1);
    armPlayOnPhrase(false);
    m_pPlayOnPhrase->forceSet(0);
    if (m_pTrack) {
        m_positionTimer.start();
    } else {
        m_positionTimer.stop();
    }
    updateStatus();
}

// static
std::optional<BarControl::DeckPosition> BarControl::positionOf(
        const QString& group, const TrackPointer& pTrack) {
    if (!pTrack) {
        return std::nullopt;
    }
    const auto pStructure = pTrack->getStructure();
    const auto pBeats = pTrack->getBeats();
    if (!pStructure || !pBeats) {
        return std::nullopt;
    }
    auto pAlignment = pStructure->alignTo(pBeats);
    // Downbeats that don't agree with the grid: don't pretend to know bars
    if (!pAlignment || pAlignment->confidence < 0.5) {
        return std::nullopt;
    }
    const double trackSamples = get(group, "track_samples");
    if (trackSamples <= 0) {
        return std::nullopt;
    }
    const auto position = mixxx::audio::FramePos::fromEngineSamplePos(
            get(group, "playposition") * trackSamples);
    if (!position.isValid()) {
        return std::nullopt;
    }
    DeckPosition pos;
    pos.pAlignment = std::move(pAlignment);
    pos.pBeats = pBeats;
    pos.beat = mixxx::TrackStructure::beatIndexAtOrBefore(*pBeats, position);
    const auto start = mixxx::TrackStructure::beatPosition(*pBeats, pos.beat);
    const auto next = mixxx::TrackStructure::beatPosition(*pBeats, pos.beat + 1);
    const double length = next - start;
    pos.fraction = length > 0 ? std::clamp((position - start) / length, 0.0, 1.0) : 0.0;
    pos.bpm = get(group, "bpm");
    pos.playing = get(group, "play") > 0;
    return pos;
}

std::optional<BarControl::DeckPosition> BarControl::ownPosition() const {
    return positionOf(m_group, m_pTrack);
}

std::optional<std::pair<QString, BarControl::DeckPosition>> BarControl::referenceDeck() const {
    std::optional<std::pair<QString, DeckPosition>> fallback;
    const int decks = static_cast<int>(
            ControlObject::get(ConfigKey(QStringLiteral("[App]"), QStringLiteral("num_decks"))));
    for (int i = 0; i < decks; ++i) {
        const QString group = PlayerManager::groupForDeck(i);
        if (group == m_group) {
            continue;
        }
        auto pos = positionOf(group, PlayerInfo::instance().getTrackInfo(group));
        if (!pos || !pos->playing) {
            continue;
        }
        if (get(group, "sync_leader") > 0) {
            return std::make_pair(group, std::move(*pos));
        }
        if (!fallback) {
            fallback = std::make_pair(group, std::move(*pos));
        }
    }
    return fallback;
}

// static
double BarControl::msUntilBeat(const DeckPosition& pos, int targetBeat) {
    if (pos.bpm <= 0) {
        return 0;
    }
    const double beats = (targetBeat - pos.beat) - pos.fraction;
    const double latencyMs = ControlObject::get(
            ConfigKey(QStringLiteral("[App]"), QStringLiteral("output_latency_ms")));
    return beats * 60000.0 / pos.bpm - latencyMs;
}

void BarControl::updateStatus() {
    const auto pos = ownPosition();
    int beatInBar = 0;
    int untilBar = 0;
    int barInPhrase = 0;
    if (pos) {
        const auto& a = *pos->pAlignment;
        beatInBar = a.beatInBar(pos->beat);
        untilBar = a.beatsUntilBar(pos->beat);
        barInPhrase = a.positionInPhrase(pos->beat) / a.beatsPerBar + 1;
    }
    // Only on change: controllers light LEDs from these
    if (m_pBeatInBar->get() != beatInBar) {
        m_pBeatInBar->forceSet(beatInBar);
    }
    if (m_pBeatsUntilBar->get() != untilBar) {
        m_pBeatsUntilBar->forceSet(untilBar);
    }
    if (m_pBarInPhrase->get() != barInPhrase) {
        m_pBarInPhrase->forceSet(barInPhrase);
    }
}

void BarControl::phraseSync() {
    const auto own = ownPosition();
    const auto refDeck = referenceDeck();
    if (!own || !refDeck) {
        return;
    }
    const DeckPosition& ref = refDeck->second;
    const auto& a = *own->pAlignment;
    const auto& r = *ref.pAlignment;
    // Compare as parts of a phrase, so grids at double or half tempo work.
    const double refInPhrase = (r.positionInPhrase(ref.beat) + ref.fraction) / r.phraseBeats;
    // The grid beat of this deck that lines up best with the reference,
    // given where this deck is inside its current beat
    const int target = static_cast<int>(
            std::floor(refInPhrase * a.phraseBeats - own->fraction + 0.5));
    const int delta = mixxx::TrackStructure::Alignment::syncDelta(
            a.positionInPhrase(own->beat),
            mixxx::TrackStructure::Alignment::floorMod(target, a.phraseBeats),
            a.phraseBeats);
    if (delta != 0) {
        set(m_group, "beatjump", delta);
    }
}

void BarControl::armPlayOnPhrase(bool arm) {
    m_playTimer.stop();
    m_playReferenceGroup.clear();
    if (!arm) {
        return;
    }
    const auto own = ownPosition();
    const auto refDeck = referenceDeck();
    if (!own || own->playing || !refDeck) {
        m_pPlayOnPhrase->forceSet(0);
        return;
    }
    const DeckPosition& ref = refDeck->second;
    int target = ref.pAlignment->nextPhraseStart(ref.beat);
    if (msUntilBeat(ref, target) < kMinLeadMs) {
        target = ref.pAlignment->nextPhraseStart(target);
    }
    m_playReferenceGroup = refDeck->first;
    m_playReferenceTarget = target;
    m_playTimer.start(static_cast<int>(std::max(0.0, msUntilBeat(ref, target))));
}

void BarControl::firePlayOnPhrase() {
    if (m_playReferenceGroup.isEmpty()) {
        return;
    }
    const auto ref = positionOf(
            m_playReferenceGroup, PlayerInfo::instance().getTrackInfo(m_playReferenceGroup));
    if (!ref || !ref->playing) {
        // The reference stopped: give up
        armPlayOnPhrase(false);
        m_pPlayOnPhrase->forceSet(0);
        return;
    }
    if (ref->beat > m_playReferenceTarget) {
        // It jumped past the phrase (loop, hot cue): wait for the next one
        m_playReferenceTarget = ref->pAlignment->nextPhraseStart(ref->beat);
    }
    const double remaining = msUntilBeat(*ref, m_playReferenceTarget);
    if (remaining > kFireWindowMs) {
        m_playTimer.start(static_cast<int>(remaining));
        return;
    }
    kLogger.info() << m_group << "starts on the phrase of" << m_playReferenceGroup;
    set(m_group, "play", 1);
    m_playReferenceGroup.clear();
    m_pPlayOnPhrase->forceSet(0);
}

void BarControl::requestStemMask(int mask) {
    m_pStemMaskPending->forceSet(mask);
    const auto own = ownPosition();
    if (!own || !own->playing) {
        applyStemMask();
        return;
    }
    m_stemTargetBeat = own->beat + own->pAlignment->beatsUntilBar(own->beat);
    m_stemTimer.start(static_cast<int>(std::max(0.0, msUntilBeat(*own, m_stemTargetBeat))));
}

void BarControl::stemMaskTimerFired() {
    const auto own = ownPosition();
    if (own && own->playing) {
        const double remaining = msUntilBeat(*own, m_stemTargetBeat);
        // Re-check: the tempo may have changed since the timer was started
        if (remaining > kFireWindowMs && own->beat < m_stemTargetBeat) {
            m_stemTimer.start(static_cast<int>(remaining));
            return;
        }
    }
    applyStemMask();
}

void BarControl::applyStemMask() {
    m_stemTimer.stop();
    const int mask = static_cast<int>(m_pStemMaskPending->get());
    m_pStemMaskPending->forceSet(-1);
    if (mask < 0) {
        return;
    }
#ifdef __STEM__
    for (int stemIdx = 0; stemIdx < mixxx::kMaxSupportedStems; ++stemIdx) {
        ControlObject* pMute = ControlObject::getControl(
                ConfigKey(EngineDeck::getGroupForStem(m_group, stemIdx), QStringLiteral("mute")),
                ControlFlag::NoWarnIfMissing);
        if (pMute) {
            pMute->set((mask & (1 << stemIdx)) ? 0.0 : 1.0);
        }
    }
#endif
}

void BarControl::loopBeats(int startBeat, int lengthBeats) {
    const auto own = ownPosition();
    if (!own || lengthBeats <= 0) {
        return;
    }
    const double start = mixxx::TrackStructure::beatPosition(*own->pBeats, startBeat)
                                 .toEngineSamplePos();
    const double end = mixxx::TrackStructure::beatPosition(
            *own->pBeats, startBeat + lengthBeats)
                               .toEngineSamplePos();
    const bool enabled = get(m_group, "loop_enabled") > 0;
    const double oldStart = get(m_group, "loop_start_position");
    const double oldEnd = get(m_group, "loop_end_position");
    if (enabled && std::abs(oldStart - start) < 2 && std::abs(oldEnd - end) < 2) {
        trigger(m_group, "reloop_toggle"); // same loop again: end it
        return;
    }
    // Never let the loop start pass its end while moving both
    if (oldEnd >= 0 && start >= oldEnd) {
        set(m_group, "loop_end_position", end);
        set(m_group, "loop_start_position", start);
    } else {
        set(m_group, "loop_start_position", start);
        set(m_group, "loop_end_position", end);
    }
    if (!enabled) {
        trigger(m_group, "reloop_toggle");
    }
}
