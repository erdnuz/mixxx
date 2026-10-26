#include "mixer/phrasecontrol.h"

#include <QFileInfo>
#include <QSet>
#include <cmath>

#include "control/controlobject.h"
#include "control/controlproxy.h"
#include "control/controlpushbutton.h"
#include "mixer/stemprepqueue.h"
#include "moc_phrasecontrol.cpp"
#include "track/track.h"
#include "track/trackstructure.h"
#include "util/color/rgbcolor.h"
#include "util/defs.h"
#include "util/logger.h"

namespace {

const mixxx::Logger kLogger("PhraseControl");

const QString kConfigGroup = QStringLiteral("[Structure]");
const QString kAutoHotcuesKey = QStringLiteral("AutoHotcues");
const QString kAutoReloadStemsKey = QStringLiteral("AutoReloadStems");
// Only fill the first 8 hot cues: that's what fits on most controllers.
constexpr int kMaxAutoHotcueSlots = 8;

} // namespace

PhraseControl::PhraseControl(const QString& group,
        UserSettingsPointer pConfig,
        QObject* pParent)
        : QObject(pParent),
          m_group(group),
          m_pConfig(pConfig) {
    m_pStructureLoaded = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("structure_loaded")));
    m_pStructureLoaded->setReadOnly();

    m_pBeatsUntilPhrase = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("beats_until_phrase")));
    m_pBeatsUntilPhrase->setReadOnly();
    m_pSectionIndex = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("section_index")));
    m_pSectionIndex->setReadOnly();
    m_pSectionIndex->forceSet(-1);
    m_pStemsReadyOnReload = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("stems_ready_on_reload")));
    m_pStemsReadyOnReload->setReadOnly();

    connect(&m_watcher,
            &QFileSystemWatcher::directoryChanged,
            this,
            &PhraseControl::slotTrackDirectoryChanged);

    m_pReload = std::make_unique<ControlPushButton>(
            ConfigKey(group, QStringLiteral("structure_reload")));
    connect(m_pReload.get(), &ControlObject::valueChanged, this, [this](double value) {
        if (value > 0 && m_pTrack) {
            m_pTrack->reloadStructure();
        }
    });

    const auto makeJump = [this, &group](std::unique_ptr<ControlPushButton>* pButton,
                                  const QString& name,
                                  Target target,
                                  int direction) {
        *pButton = std::make_unique<ControlPushButton>(ConfigKey(group, name));
        connect(pButton->get(),
                &ControlObject::valueChanged,
                this,
                [this, target, direction](double value) {
                    if (value > 0) {
                        jump(target, direction);
                    }
                });
    };
    makeJump(&m_pPhraseForward, QStringLiteral("phrase_jump_forward"), Target::Phrase, 1);
    makeJump(&m_pPhraseBackward, QStringLiteral("phrase_jump_backward"), Target::Phrase, -1);
    makeJump(&m_pSectionForward, QStringLiteral("section_jump_forward"), Target::Section, 1);
    makeJump(&m_pSectionBackward,
            QStringLiteral("section_jump_backward"),
            Target::Section,
            -1);

    m_pPlayPosition = make_parented<ControlProxy>(group, QStringLiteral("playposition"), this);
    m_pPlayPosition->connectValueChanged(this, &PhraseControl::slotPositionChanged);
    m_pPlay = make_parented<ControlProxy>(group, QStringLiteral("play"), this);
    m_pPlay->connectValueChanged(this, &PhraseControl::slotPlayChanged);
    m_pTrackSamples = make_parented<ControlProxy>(group, QStringLiteral("track_samples"), this);
    m_pBeatJump = make_parented<ControlProxy>(group, QStringLiteral("beatjump"), this);
}

PhraseControl::~PhraseControl() = default;

void PhraseControl::trackLoaded(TrackPointer pTrack) {
    if (m_pTrack) {
        disconnect(m_pTrack.get(), nullptr, this, nullptr);
    }
    m_pTrack = std::move(pTrack);
    m_pCuesAddedTrack = nullptr;
    m_cuesAddedFinal = false;
    m_updateCuesWhenStopped = false;
    if (m_pTrack) {
        connect(m_pTrack.get(),
                &Track::structureUpdated,
                this,
                &PhraseControl::slotStructureOrBeatsChanged);
        connect(m_pTrack.get(),
                &Track::beatsUpdated,
                this,
                &PhraseControl::slotStructureOrBeatsChanged);
        // Pick up files written by stemprep since the track was last loaded.
        m_pTrack->reloadStructure();
        // The reader has just opened the track the same way
        m_loadedStemCache = mixxx::TrackStructure::stemCacheFor(
                m_pTrack->getLocation(), m_pTrack->getSampleRate());
        if (isDeck()) {
            StemprepQueue::request(
                    m_pTrack->getLocation(), StemprepQueue::kPriorityDeck, m_pConfig);
        }
    } else {
        m_loadedStemCache.clear();
    }
    m_reloadWhenStopped = false;
    watchSidecar();
    updateStemsReady();
    slotStructureOrBeatsChanged();
}

bool PhraseControl::isDeck() const {
    return m_group.startsWith(QStringLiteral("[Channel")); // not samplers or preview
}

void PhraseControl::watchSidecar() {
    const QStringList watched = m_watcher.directories();
    if (!watched.isEmpty()) {
        m_watcher.removePaths(watched);
    }
    m_sidecarModified = QDateTime();
    if (!m_pTrack || !isDeck()) {
        return;
    }
    const QFileInfo sidecar(mixxx::TrackStructure::sidecarPath(m_pTrack->getLocation()));
    if (sidecar.exists()) {
        m_sidecarModified = sidecar.lastModified();
    }
    m_watcher.addPath(sidecar.absolutePath());
}

void PhraseControl::slotTrackDirectoryChanged() {
    if (!m_pTrack) {
        return;
    }
    // Something in the track's folder changed; only react to the structure file
    const QFileInfo sidecar(mixxx::TrackStructure::sidecarPath(m_pTrack->getLocation()));
    const QDateTime modified = sidecar.exists() ? sidecar.lastModified() : QDateTime();
    if (modified == m_sidecarModified) {
        return;
    }
    m_sidecarModified = modified;
    m_pTrack->reloadStructure(); // emits structureUpdated() if it changed
    updateStemsReady();
}

void PhraseControl::updateStemsReady() {
    bool ready = false;
    if (m_pTrack) {
        const QString stemCache = mixxx::TrackStructure::stemCacheFor(
                m_pTrack->getLocation(), m_pTrack->getSampleRate());
        ready = !stemCache.isEmpty() && stemCache != m_loadedStemCache;
    }
    m_pStemsReadyOnReload->forceSet(ready ? 1.0 : 0.0);
    if (!ready || !isDeck() ||
            !m_pConfig->getValue(ConfigKey(kConfigGroup, kAutoReloadStemsKey), true)) {
        m_reloadWhenStopped = false;
        return;
    }
    // Switching the audio file under a playing deck would interrupt it
    if (m_pPlay->toBool()) {
        m_reloadWhenStopped = true;
    } else {
        kLogger.info() << m_group << "switching to new stems";
        emit reloadForNewStems();
    }
}

void PhraseControl::slotPlayChanged(double play) {
    if (play == 0 && m_reloadWhenStopped) {
        m_reloadWhenStopped = false;
        updateStemsReady(); // still new? then reload now
    }
    if (play == 0 && m_updateCuesWhenStopped) {
        m_updateCuesWhenStopped = false;
        slotStructureOrBeatsChanged();
    }
}

void PhraseControl::slotStructureOrBeatsChanged() {
    const TrackPointer pTrack = m_pTrack;
    const bool loaded = pTrack && pTrack->getStructure();
    m_pStructureLoaded->forceSet(loaded ? 1.0 : 0.0);
    if (loaded) {
        maybeAddCues(pTrack);
    }
    updateStatus();
}

void PhraseControl::slotPositionChanged(double playPosition) {
    Q_UNUSED(playPosition);
    updateStatus();
}

bool PhraseControl::currentBeat(const TrackPointer& pTrack, int* pBeatIndex) const {
    const auto pBeats = pTrack->getBeats();
    const double trackSamples = m_pTrackSamples->get();
    if (!pBeats || trackSamples <= 0) {
        return false;
    }
    const auto position = mixxx::audio::FramePos::fromEngineSamplePos(
            m_pPlayPosition->get() * trackSamples);
    if (!position.isValid()) {
        return false;
    }
    *pBeatIndex = mixxx::TrackStructure::beatIndexAtOrBefore(*pBeats, position);
    return true;
}

void PhraseControl::updateStatus() {
    const TrackPointer pTrack = m_pTrack;
    const auto pStructure = pTrack ? pTrack->getStructure() : nullptr;
    const auto pBeats = pTrack ? pTrack->getBeats() : nullptr;
    int beat = 0;
    if (!pStructure || !pBeats || !currentBeat(pTrack, &beat)) {
        m_pBeatsUntilPhrase->forceSet(0);
        m_pSectionIndex->forceSet(-1);
        return;
    }
    const auto pAlignment = pStructure->alignTo(pBeats);
    if (!pAlignment) {
        return;
    }
    int until = 0;
    for (int phrase : pAlignment->sortedPhraseStarts()) {
        if (phrase > beat) {
            until = phrase - beat;
            break;
        }
    }
    m_pBeatsUntilPhrase->forceSet(until);
    int sectionIndex = -1;
    for (int i = 0; i < pAlignment->sections.size(); ++i) {
        const auto& section = pAlignment->sections.at(i);
        if (beat >= section.startBeat && beat < section.endBeat) {
            sectionIndex = i;
            break;
        }
    }
    m_pSectionIndex->forceSet(sectionIndex);
}

void PhraseControl::jump(Target target, int direction) {
    const TrackPointer pTrack = m_pTrack;
    if (!pTrack) {
        return;
    }
    const auto pStructure = pTrack->getStructure();
    const auto pBeats = pTrack->getBeats();
    int beat = 0;
    if (!pStructure || !pBeats || !currentBeat(pTrack, &beat)) {
        return;
    }
    const auto pAlignment = pStructure->alignTo(pBeats);
    if (!pAlignment) {
        return;
    }

    QList<int> starts;
    if (target == Target::Phrase) {
        starts = pAlignment->sortedPhraseStarts();
    } else {
        for (const auto& section : pAlignment->sections) {
            starts.append(section.startBeat);
        }
    }
    if (starts.isEmpty()) {
        return;
    }

    // Jump by whole bars measured from the start of the current bar, so the
    // position inside the bar (and the phase against other decks) is kept.
    const int barStart = pAlignment->barStartAtOrBefore(beat);
    int destination = 0;
    bool found = false;
    if (direction > 0) {
        for (int start : starts) {
            if (start > barStart) {
                destination = start;
                found = true;
                break;
            }
        }
    } else {
        for (auto it = starts.crbegin(); it != starts.crend(); ++it) {
            if (*it < barStart) {
                destination = *it;
                found = true;
                break;
            }
        }
    }
    if (!found) {
        return;
    }
    m_pBeatJump->set(static_cast<double>(destination - barStart));
}

void PhraseControl::maybeAddCues(const TrackPointer& pTrack) {
    if (!isDeck()) {
        return;
    }
    if (!m_pConfig->getValue(ConfigKey(kConfigGroup, kAutoHotcuesKey), true)) {
        return;
    }
    const auto pStructure = pTrack->getStructure();
    const auto pBeats = pTrack->getBeats();
    if (!pStructure || !pBeats || pStructure->cuesApplied()) {
        return;
    }
    // Sections from the mix only may still move once stems are made: their
    // cues are added now and replaced by the ones from the stems analysis,
    // as long as the user hasn't touched them.
    const bool isFinal = pStructure->analyzedFromStems();
    if (m_pCuesAddedTrack == pTrack.get() && (m_cuesAddedFinal || !isFinal)) {
        return; // done during this load (the sidecar may be read-only)
    }
    const auto& previous = pStructure->autoCues();
    if (!isFinal && !previous.isEmpty()) {
        return; // the cues of the mix analysis are in already
    }
    if (previous.isEmpty() && pStructure->cueSuggestions().isEmpty()) {
        return;
    }
    if (!previous.isEmpty() && m_pPlay->toBool()) {
        // Don't move cues under a playing deck
        m_updateCuesWhenStopped = true;
        return;
    }
    const auto pAlignment = pStructure->alignTo(pBeats);
    if (!pAlignment || pAlignment->confidence < 0.5) {
        // The downbeats don't agree with this beat grid; don't add cues in
        // the wrong place.
        kLogger.info() << "Not adding structure cues: downbeat confidence"
                       << (pAlignment ? pAlignment->confidence : 0.0);
        return;
    }

    m_pCuesAddedTrack = pTrack.get();
    m_cuesAddedFinal = isFinal;

    // Automatic cues still where Mixxx put them are replaced; for moved,
    // renamed or deleted ones the user's choice stands.
    QSet<QString> userLabels;
    int removed = 0;
    for (const auto& autoCue : previous) {
        const CuePointer pCue = pTrack->findHotcueByIndex(autoCue.slot);
        if (pCue && pCue->getLabel() == autoCue.label &&
                std::abs(pCue->getPosition().value() - autoCue.frame) < 1.0) {
            pTrack->removeCue(pCue);
            removed++;
        } else {
            userLabels.insert(autoCue.label);
        }
    }

    QList<bool> usedSlots(kMaxAutoHotcueSlots, false);
    QList<mixxx::audio::FramePos> existing;
    for (const auto& pCue : pTrack->getCuePoints()) {
        if (pCue->getType() != mixxx::CueType::HotCue) {
            continue;
        }
        const int index = pCue->getHotCue();
        if (index >= 0 && index < kMaxAutoHotcueSlots) {
            usedSlots[index] = true;
        }
        existing.append(pCue->getPosition());
    }

    QList<mixxx::TrackStructure::AutoCue> added;
    for (const auto& suggestion : pStructure->cueSuggestions()) {
        if (userLabels.contains(suggestion.label)) {
            continue;
        }
        const auto index = mixxx::TrackStructure::closestBeatIndex(
                *pBeats, suggestion.positionSeconds);
        if (!index) {
            continue;
        }
        const auto position = mixxx::TrackStructure::beatPosition(
                *pBeats, pAlignment->snapToBar(*index));
        if (!position.isValid()) {
            continue;
        }
        // Skip if the user already has a hot cue within a beat of it.
        const auto beatLength = std::abs(
                mixxx::TrackStructure::beatPosition(*pBeats, *index + 1) -
                mixxx::TrackStructure::beatPosition(*pBeats, *index));
        bool duplicate = false;
        for (const auto& other : existing) {
            if (other.isValid() && std::abs(other - position) < beatLength) {
                duplicate = true;
                break;
            }
        }
        if (duplicate) {
            continue;
        }
        int slot = usedSlots.indexOf(false);
        if (slot < 0) {
            break;
        }
        usedSlots[slot] = true;
        const auto color = mixxx::RgbColor::fromQColor(suggestion.color,
                mixxx::PredefinedColorPalettes::kDefaultCueColor);
        CuePointer pCue = pTrack->createAndAddCue(mixxx::CueType::HotCue,
                slot,
                position,
                mixxx::audio::kInvalidFramePos,
                color.value_or(mixxx::PredefinedColorPalettes::kDefaultCueColor));
        if (pCue) {
            pCue->setLabel(suggestion.label);
            existing.append(position);
            added.append({slot, position.value(), suggestion.label});
        }
    }
    kLogger.info() << "Added" << added.size() << "structure hot cues (replaced" << removed
                   << ") to" << pTrack->getInfo() << (isFinal ? "" : "from the mix analysis");
    if (mixxx::TrackStructure::recordAutoCues(pTrack->getLocation(), added, isFinal)) {
        // Re-read so autoCues()/cuesApplied() are up to date in memory too
        pTrack->reloadStructure();
    }
}
