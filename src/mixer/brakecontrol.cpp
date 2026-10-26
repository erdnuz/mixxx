#include "mixer/brakecontrol.h"

#include <cmath>

#include "control/controlobject.h"
#include "control/controlproxy.h"
#include "control/controlpushbutton.h"
#include "moc_brakecontrol.cpp"
#include "util/math.h"

namespace {

constexpr double kDefaultBrakeSeconds = 2.0;
constexpr double kDefaultSoftStartSeconds = 0.8;
// Below this the deck counts as stopped (same as engine.brake()).
constexpr double kStoppedRate = 0.01;
constexpr int kTickMs = 5;

} // namespace

BrakeControl::BrakeControl(const QString& group, QObject* pParent)
        : QObject(pParent) {
    m_pBrake = std::make_unique<ControlPushButton>(ConfigKey(group, QStringLiteral("brake")));
    connect(m_pBrake.get(), &ControlObject::valueChanged, this, [this](double value) {
        if (value > 0) {
            brakeOrSpinUp();
        }
    });
    m_pBrakeActive = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("brake_active")));
    m_pBrakeActive->setReadOnly();
    m_pBrakeTime = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("brake_time")),
            true,
            false,
            true, // persist
            kDefaultBrakeSeconds);
    m_pSoftStartTime = std::make_unique<ControlObject>(
            ConfigKey(group, QStringLiteral("softstart_time")),
            true,
            false,
            true, // persist
            kDefaultSoftStartSeconds);

    m_pPlay = make_parented<ControlProxy>(group, QStringLiteral("play"), this);
    m_pScratch2 = make_parented<ControlProxy>(group, QStringLiteral("scratch2"), this);
    m_pScratch2Enable = make_parented<ControlProxy>(group, QStringLiteral("scratch2_enable"), this);
    m_pRateRatio = make_parented<ControlProxy>(group, QStringLiteral("rate_ratio"), this);
    m_pReverse = make_parented<ControlProxy>(group, QStringLiteral("reverse"), this);
    m_pTrackLoaded = make_parented<ControlProxy>(group, QStringLiteral("track_loaded"), this);

    m_timer.setTimerType(Qt::PreciseTimer);
    m_timer.setInterval(kTickMs);
    connect(&m_timer, &QTimer::timeout, this, &BrakeControl::slotTick);
}

BrakeControl::~BrakeControl() = default;

double BrakeControl::deckRate() const {
    const double rate = m_pRateRatio->get();
    return m_pReverse->toBool() ? -rate : rate;
}

void BrakeControl::brakeOrSpinUp() {
    if (!m_pTrackLoaded->toBool()) {
        return;
    }
    if (m_mode == Mode::Braking) {
        // Spin back up from wherever the brake is now.
        start(Mode::SpinningUp, m_currentRate, deckRate(), m_pSoftStartTime->get());
    } else if (m_mode == Mode::SpinningUp) {
        start(Mode::Braking, m_currentRate, 0, m_pBrakeTime->get());
    } else if (m_pPlay->toBool()) {
        const double rate = deckRate();
        if (std::abs(rate) < kStoppedRate) {
            m_pPlay->set(0);
            return;
        }
        start(Mode::Braking, rate, 0, m_pBrakeTime->get());
    } else {
        start(Mode::SpinningUp, 0, deckRate(), m_pSoftStartTime->get());
    }
}

void BrakeControl::start(Mode mode, double fromRate, double toRate, double seconds) {
    m_mode = mode;
    m_fromRate = fromRate;
    m_toRate = toRate;
    // Scale by the distance still to go, so reversing halfway takes half the time.
    const double fullRange = std::max(std::abs(deckRate()), kStoppedRate);
    const double fraction = math_clamp(std::abs(toRate - fromRate) / fullRange, 0.0, 1.0);
    m_durationMs = std::max(0.0, seconds) * 1000.0 * fraction;
    m_currentRate = fromRate;

    m_pScratch2->set(fromRate);
    m_pScratch2Enable->set(1);
    if (mode == Mode::SpinningUp) {
        m_pPlay->set(1);
    }
    m_pBrakeActive->forceSet(1);
    m_elapsed.start();
    m_timer.start();
    slotTick();
}

void BrakeControl::slotTick() {
    if (m_mode == Mode::Idle) {
        m_timer.stop();
        return;
    }
    // Give up if the track was ejected or the user stopped the deck.
    if (!m_pTrackLoaded->toBool() || !m_pPlay->toBool()) {
        finish(false);
        return;
    }
    const double progress = m_durationMs > 0
            ? math_clamp(m_elapsed.elapsed() / m_durationMs, 0.0, 1.0)
            : 1.0;
    // S-curve: slow change at the start and the end, like a platter
    const double eased = (1.0 - std::cos(M_PI * progress)) / 2.0;
    m_currentRate = m_fromRate + (m_toRate - m_fromRate) * eased;
    m_pScratch2->set(m_currentRate);
    if (progress >= 1.0) {
        finish(m_mode == Mode::Braking);
    }
}

void BrakeControl::finish(bool stopDeck) {
    m_timer.stop();
    m_mode = Mode::Idle;
    if (stopDeck) {
        m_pScratch2->set(0);
        m_pPlay->set(0);
    }
    // Back to normal playback (at the deck's own rate after a spin-up)
    m_pScratch2Enable->set(0);
    m_pBrakeActive->forceSet(0);
}
