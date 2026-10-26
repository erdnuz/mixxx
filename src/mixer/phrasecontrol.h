#pragma once

#include <QDateTime>
#include <QFileSystemWatcher>
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
///   [ChannelN],stems_ready_on_reload  1 if stemprep made (better) stems for
///                                     the loaded track; they play after
///                                     loading it again
///
/// When a track's structure data appears, the suggested hot cues (BUILD,
/// DROP, BREAKDOWN...) are added to free hot cue slots, unless
/// [Structure],AutoHotcues is 0. Cues from an analysis of the full mix are
/// replaced by those of the stems analysis (while the deck is stopped),
/// except cues the user moved, renamed or deleted.
///
/// Loading a track into a deck asks stemprep for stems (StemprepQueue); the
/// structure file is watched, so sections appear and improve while the track
/// is loaded.
class PhraseControl : public QObject {
    Q_OBJECT
  public:
    PhraseControl(const QString& group, UserSettingsPointer pConfig, QObject* pParent);
    ~PhraseControl() override;

    void trackLoaded(TrackPointer pTrack);

  signals:
    /// stemprep made (better) stems for the loaded track and the deck is
    /// stopped: the player reloads the track to play them. While the deck
    /// plays this waits until it stops ([Structure],AutoReloadStems = 0: off).
    void reloadForNewStems();

  private slots:
    void slotPlayChanged(double play);
    void slotStructureOrBeatsChanged();
    void slotPositionChanged(double playPosition);
    void slotTrackDirectoryChanged();

  private:
    enum class Target {
        Phrase,
        Section,
    };
    void jump(Target target, int direction);
    void maybeAddCues(const TrackPointer& pTrack);
    void updateStatus();
    void watchSidecar();
    void updateStemsReady();
    bool isDeck() const;
    /// Index of the grid beat at or before the play position; false if unknown.
    bool currentBeat(const TrackPointer& pTrack, int* pBeatIndex) const;

    const QString m_group;
    UserSettingsPointer m_pConfig;
    TrackPointer m_pTrack;
    // Track for which hot cues were already added during this load, so a
    // read-only structure file can't make us add them again and again.
    const Track* m_pCuesAddedTrack = nullptr;
    // ... and whether they came from the stems analysis (final)
    bool m_cuesAddedFinal = false;
    // Cues from the stems analysis arrived while the deck was playing
    bool m_updateCuesWhenStopped = false;

    std::unique_ptr<ControlObject> m_pStructureLoaded;
    std::unique_ptr<ControlPushButton> m_pReload;
    std::unique_ptr<ControlPushButton> m_pPhraseForward;
    std::unique_ptr<ControlPushButton> m_pPhraseBackward;
    std::unique_ptr<ControlPushButton> m_pSectionForward;
    std::unique_ptr<ControlPushButton> m_pSectionBackward;
    std::unique_ptr<ControlObject> m_pBeatsUntilPhrase;
    std::unique_ptr<ControlObject> m_pSectionIndex;
    std::unique_ptr<ControlObject> m_pStemsReadyOnReload;

    // The structure file is replaced by renaming, so the folder is watched
    // and the file's time stamp compared.
    QFileSystemWatcher m_watcher;
    QDateTime m_sidecarModified;
    // Stem file the loaded track is playing from (empty: its own file)
    QString m_loadedStemCache;
    // New stems arrived while the deck was playing
    bool m_reloadWhenStopped = false;

    parented_ptr<ControlProxy> m_pPlayPosition;
    parented_ptr<ControlProxy> m_pPlay;
    parented_ptr<ControlProxy> m_pTrackSamples;
    parented_ptr<ControlProxy> m_pBeatJump;
};
