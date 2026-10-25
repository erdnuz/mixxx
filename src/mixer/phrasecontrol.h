#pragma once

#include <QObject>
#include <memory>

#include "preferences/usersettings.h"
#include "track/track_decl.h"
#include "util/parented_ptr.h"

class ControlObject;
class ControlProxy;
class ControlPushButton;

/// Per-deck controls built on the track's bar/phrase/section structure
/// (see mixxx::TrackStructure):
///
///   [ChannelN],structure_loaded       1 if the loaded track has structure data
///   [ChannelN],structure_reload       re-read <file>.structure.json
///   [ChannelN],phrase_jump_forward    jump to the next phrase, keeping the
///   [ChannelN],phrase_jump_backward   position inside the bar (beat-exact)
///   [ChannelN],section_jump_forward   same, to the next/previous section
///   [ChannelN],section_jump_backward  (Intro, Build, Drop, Breakdown...)
///   [ChannelN],beats_until_phrase     beats left until the next phrase
///   [ChannelN],section_index          index of the current section, -1 if none
///
/// When a track with structure data is loaded for the first time, the
/// suggested hot cues (BUILD, DROP, BREAKDOWN...) are added to free hot cue
/// slots, unless [Structure],AutoHotcues is 0.
class PhraseControl : public QObject {
    Q_OBJECT
  public:
    PhraseControl(const QString& group, UserSettingsPointer pConfig, QObject* pParent);
    ~PhraseControl() override;

    void trackLoaded(TrackPointer pTrack);

  private slots:
    void slotStructureOrBeatsChanged();
    void slotPositionChanged(double playPosition);

  private:
    enum class Target {
        Phrase,
        Section,
    };
    void jump(Target target, int direction);
    void maybeAddCues(const TrackPointer& pTrack);
    void updateStatus();
    /// Index of the grid beat at or before the play position; false if unknown.
    bool currentBeat(const TrackPointer& pTrack, int* pBeatIndex) const;

    const QString m_group;
    UserSettingsPointer m_pConfig;
    TrackPointer m_pTrack;
    // Track for which hot cues were already added during this load, so a
    // read-only structure file can't make us add them again and again.
    const Track* m_pCuesAddedTrack = nullptr;

    std::unique_ptr<ControlObject> m_pStructureLoaded;
    std::unique_ptr<ControlPushButton> m_pReload;
    std::unique_ptr<ControlPushButton> m_pPhraseForward;
    std::unique_ptr<ControlPushButton> m_pPhraseBackward;
    std::unique_ptr<ControlPushButton> m_pSectionForward;
    std::unique_ptr<ControlPushButton> m_pSectionBackward;
    std::unique_ptr<ControlObject> m_pBeatsUntilPhrase;
    std::unique_ptr<ControlObject> m_pSectionIndex;

    parented_ptr<ControlProxy> m_pPlayPosition;
    parented_ptr<ControlProxy> m_pTrackSamples;
    parented_ptr<ControlProxy> m_pBeatJump;
};
