#pragma once

#include <QElapsedTimer>
#include <QObject>
#include <QTimer>
#include <memory>

#include "util/parented_ptr.h"

class ControlObject;
class ControlProxy;
class ControlPushButton;

/// Turntable-style brake and spin-up for a deck, so skins (and mappings)
/// can use it without the controller script engine:
///
///   [ChannelN],brake            press: slow the playing deck down to a stop;
///                               press again while stopped or braking: spin
///                               back up to the normal speed
///   [ChannelN],brake_active     1 while braking or spinning up (read-only)
///   [ChannelN],brake_time       seconds from full speed to stop (default 2)
///   [ChannelN],softstart_time   seconds from stop to full speed (default 0.8)
///
/// Like engine.brake()/engine.softStart() in controller scripts it drives
/// scratch2, so the pitch goes down with the speed. The speed follows a
/// smooth S-curve computed from the elapsed time, so a busy GUI thread
/// doesn't change how long the brake takes.
class BrakeControl : public QObject {
    Q_OBJECT
  public:
    BrakeControl(const QString& group, QObject* pParent);
    ~BrakeControl() override;

  private slots:
    void slotTick();

  private:
    enum class Mode {
        Idle,
        Braking,
        SpinningUp,
    };
    void brakeOrSpinUp();
    void start(Mode mode, double fromRate, double toRate, double seconds);
    /// End the ramp. stopDeck: also set play to 0 (end of a brake).
    void finish(bool stopDeck);
    /// Normal playback speed (tempo slider, direction).
    double deckRate() const;

    Mode m_mode = Mode::Idle;
    double m_fromRate = 0;
    double m_toRate = 0;
    double m_durationMs = 0;
    double m_currentRate = 0;
    QElapsedTimer m_elapsed;
    QTimer m_timer;

    std::unique_ptr<ControlPushButton> m_pBrake;
    std::unique_ptr<ControlObject> m_pBrakeActive;
    std::unique_ptr<ControlObject> m_pBrakeTime;
    std::unique_ptr<ControlObject> m_pSoftStartTime;

    parented_ptr<ControlProxy> m_pPlay;
    parented_ptr<ControlProxy> m_pScratch2;
    parented_ptr<ControlProxy> m_pScratch2Enable;
    parented_ptr<ControlProxy> m_pRateRatio;
    parented_ptr<ControlProxy> m_pReverse;
    parented_ptr<ControlProxy> m_pTrackLoaded;
};
