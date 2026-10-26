#pragma once

#include <QObject>
#include <QString>
#include <QTimer>
#include <memory>
#include <optional>
#include <utility>

#include "track/track_decl.h"
#include "track/trackstructure.h"

class ControlObject;
class ControlPushButton;

/// Bar- and phrase-aware performance controls, built on the track's
/// structure (mixxx::TrackStructure; inert for tracks without it):
///
///   [ChannelN],beat_in_bar        1..4 (0 = unknown), read-only
///   [ChannelN],beats_until_bar    beats to the next downbeat, read-only
///   [ChannelN],bar_in_phrase      1..8 (0 = unknown), read-only
///   [ChannelN],phrase_sync        move this deck by whole beats so its place
///                                 in the phrase matches the reference deck
///   [ChannelN],play_on_phrase     1 = start playing exactly when the
///                                 reference deck reaches its next phrase
///                                 (cue this deck at a phrase start first);
///                                 back to 0 once started, set 0 to cancel
///   [ChannelN],stem_mask_on_bar   set to a bitmask of the stems that should
///                                 be audible (bit 0 = stem 1): applied at
///                                 the next downbeat (at once if stopped)
///   [ChannelN],stem_mask_pending  that mask while waiting, else -1
///   [ChannelN],bar_loop           set N: loop N bars from the current bar's
///                                 downbeat; the same N again ends it
///   [ChannelN],phrase_loop        loop the current phrase (or end that loop)
///   [ChannelN],phrase_restart     jump back to the start of the current
///                                 phrase, keeping the place in the bar
///
/// Cue sync: make a cue of this (stopped) deck land exactly on a cue of the
/// playing deck: double drops (their DROP + my DROP), handovers (their
/// BREAKDOWN or OUTRO + my DROP), anything else.
///   [ChannelN],cue_sync_mine      hot cue number (1..) on this deck; 0 = its
///                                 first cue labelled DROP; -1 = its next
///                                 hot cue from where it is cued
///   [ChannelN],cue_sync_theirs    hot cue number on the other deck; 0 = its
///                                 next cue labelled DROP; -1 = its next hot
///                                 cue
///   [ChannelN],cue_sync_deck      the other deck (1..4); 0 = the reference
///                                 deck (see below)
///   [ChannelN],cue_sync_lead_bars bars of this deck played before its cue
///                                 (default 8; fewer if the track is shorter)
///   [ChannelN],cue_sync           1 = arm: enables sync, cues this deck the
///                                 lead before its cue and starts it so the
///                                 two cues meet; 0 again once started; set 0
///                                 to cancel
///
/// Sync in steps (the SYNC button's tap):
///   [ChannelN],sync_step          each press does the next step against the
///                                 reference deck. Playing deck: 1. beats
///                                 (beatsync) 2. bars (jump by whole beats so
///                                 the downbeats meet) 3. cues (jump by whole
///                                 bars so this deck's next hot cue lands on
///                                 the reference's next hot cue). Stopped
///                                 deck: 1. tempo + place in the phrase
///                                 2. cue sync of the next hot cues (again =
///                                 cancel). Done steps are skipped, so a synced
///                                 deck goes on to bars. A deck without hot
///                                 cues uses its section starts.
///
/// The reference deck is the sync leader if it is another playing deck with
/// structure, else another playing deck with structure.
///
/// Timed actions run on the GUI thread with a precise timer, started early
/// by the audio output latency, and re-checked when they fire.
class BarControl : public QObject {
    Q_OBJECT
  public:
    BarControl(const QString& group, QObject* pParent);
    ~BarControl() override;

    void trackLoaded(TrackPointer pTrack);

  private:
    /// Where a deck is on its grid right now.
    struct DeckPosition {
        std::shared_ptr<const mixxx::TrackStructure::Alignment> pAlignment;
        mixxx::BeatsPointer pBeats;
        int beat = 0;           // grid beat at or before the play position
        double fraction = 0;    // part of that beat already played (0..1)
        double bpm = 0;         // current tempo
        bool playing = false;
    };
    static std::optional<DeckPosition> positionOf(const QString& group, const TrackPointer& pTrack);
    std::optional<DeckPosition> ownPosition() const;
    /// Another playing deck with structure, preferring the sync leader:
    /// its group and position.
    std::optional<std::pair<QString, DeckPosition>> referenceDeck() const;
    /// Milliseconds until `pos` reaches grid beat `targetBeat`, minus the
    /// output latency (so the action is heard on time).
    static double msUntilBeat(const DeckPosition& pos, int targetBeat);

    void updateStatus();
    /// Returns the beats jumped.
    int phraseSync();
    void syncStep();
    /// Jump by whole bars so the next hot cues of both decks meet.
    void nextCueSync(const DeckPosition& own, const QString& refGroup, const DeckPosition& ref);
    void armPlayOnPhrase(bool arm);
    void armCueSync(bool arm);
    /// cue_sync with these cues and deck (see cue_sync_mine/theirs/deck)
    void armCueSyncWith(int mineHotcue, int theirsHotcue, int deck);
    /// Start this deck when `referenceGroup` reaches grid beat `targetBeat`.
    /// followPhrases: if the reference jumps past it, wait for its next
    /// phrase (play_on_phrase); otherwise give up (cue_sync).
    void startPlayAt(const QString& referenceGroup, int targetBeat, bool followPhrases);
    void cancelPlayStart();
    void firePlayStart();
    /// Grid beat of a hot cue (1-based number; 0 = first drop, -1 = first hot
    /// cue, at or after fromBeat), or nothing.
    static std::optional<int> cueBeat(
            const TrackPointer& pTrack, const DeckPosition& pos, int hotcue, int fromBeat);
    /// Grid beats of the hot cues whose label starts with label (empty:
    /// all), sorted; if there are none, the starts of such sections.
    static QList<int> cueBeats(
            const TrackPointer& pTrack, const DeckPosition& pos, const QString& label);
    /// Grid beat closest to a frame position.
    static int closestBeat(const DeckPosition& pos, mixxx::audio::FramePos position);
    void requestStemMask(int mask);
    void applyStemMask();
    void loopBeats(int startBeat, int lengthBeats);
    void stemMaskTimerFired();

    const QString m_group;
    TrackPointer m_pTrack;

    std::unique_ptr<ControlObject> m_pBeatInBar;
    std::unique_ptr<ControlObject> m_pBeatsUntilBar;
    std::unique_ptr<ControlObject> m_pBarInPhrase;
    std::unique_ptr<ControlPushButton> m_pPhraseSync;
    std::unique_ptr<ControlPushButton> m_pSyncStep;
    // Stopped deck: the first step left this track at this beat position
    const Track* m_pSyncStepTrack = nullptr;
    double m_syncStepPosition = 0;
    std::unique_ptr<ControlObject> m_pPlayOnPhrase;
    std::unique_ptr<ControlObject> m_pStemMaskOnBar;
    std::unique_ptr<ControlObject> m_pStemMaskPending;
    std::unique_ptr<ControlObject> m_pBarLoop;
    std::unique_ptr<ControlPushButton> m_pPhraseLoop;
    std::unique_ptr<ControlPushButton> m_pPhraseRestart;
    std::unique_ptr<ControlObject> m_pCueSyncMine;
    std::unique_ptr<ControlObject> m_pCueSyncTheirs;
    std::unique_ptr<ControlObject> m_pCueSyncDeck;
    std::unique_ptr<ControlObject> m_pCueSyncLeadBars;
    std::unique_ptr<ControlObject> m_pCueSync;

    QTimer m_positionTimer;
    QTimer m_stemTimer;
    int m_stemTargetBeat = 0;
    QTimer m_playTimer;
    QString m_playReferenceGroup;
    int m_playReferenceTarget = 0;
    bool m_playFollowsPhrases = false;
};
