#include <gtest/gtest.h>

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QThread>
#include <memory>
#include <vector>

#include "control/controlobject.h"
#include "mixer/brakecontrol.h"
#include "test/mixxxtest.h"

namespace {

const QString kGroup = QStringLiteral("[BrakeTest]");

ConfigKey key(const char* item) {
    return ConfigKey(kGroup, QString::fromLatin1(item));
}

class BrakeControlTest : public MixxxTest {
  protected:
    void SetUp() override {
        // Stand-ins for the deck's engine controls
        for (const char* item :
                {"play", "scratch2", "scratch2_enable", "rate_ratio", "reverse", "track_loaded"}) {
            m_controls.push_back(std::make_unique<ControlObject>(key(item)));
        }
        ControlObject::set(key("rate_ratio"), 1.0);
        ControlObject::set(key("track_loaded"), 1.0);
        m_pBrake = std::make_unique<BrakeControl>(kGroup, nullptr);
        ControlObject::set(key("brake_time"), 0.1);
        ControlObject::set(key("softstart_time"), 0.1);
    }

    static double get(const char* item) {
        return ControlObject::get(key(item));
    }

    static void press() {
        ControlObject::set(key("brake"), 1.0);
        ControlObject::set(key("brake"), 0.0);
    }

    /// Runs the event loop until the brake/spin-up is over; returns the
    /// scratch2 values seen on the way.
    static std::vector<double> waitUntilDone() {
        std::vector<double> rates;
        QElapsedTimer timer;
        timer.start();
        while (get("brake_active") > 0 && timer.elapsed() < 2000) {
            QCoreApplication::processEvents(QEventLoop::AllEvents, 5);
            QThread::msleep(1);
            rates.push_back(get("scratch2"));
        }
        return rates;
    }

    std::vector<std::unique_ptr<ControlObject>> m_controls;
    std::unique_ptr<BrakeControl> m_pBrake;
};

TEST_F(BrakeControlTest, BrakeSlowsDownToAStop) {
    ControlObject::set(key("play"), 1.0);
    press();
    EXPECT_EQ(1.0, get("brake_active"));
    EXPECT_EQ(1.0, get("scratch2_enable"));
    EXPECT_NEAR(1.0, get("scratch2"), 0.05);

    const auto rates = waitUntilDone();
    EXPECT_EQ(0.0, get("brake_active"));
    EXPECT_EQ(0.0, get("play"));
    EXPECT_EQ(0.0, get("scratch2_enable"));
    EXPECT_EQ(0.0, get("scratch2"));
    ASSERT_FALSE(rates.empty());
    for (size_t i = 1; i < rates.size(); ++i) {
        EXPECT_LE(rates[i], rates[i - 1] + 1e-9);
    }
}

TEST_F(BrakeControlTest, PressWhileStoppedSpinsUp) {
    ControlObject::set(key("rate_ratio"), 1.08); // tempo slider +8%
    press();
    EXPECT_EQ(1.0, get("play"));
    EXPECT_EQ(1.0, get("brake_active"));

    waitUntilDone();
    EXPECT_EQ(0.0, get("brake_active"));
    EXPECT_EQ(1.0, get("play"));
    // Back to normal playback at the deck's own speed
    EXPECT_EQ(0.0, get("scratch2_enable"));
    EXPECT_NEAR(1.08, get("scratch2"), 1e-6);
}

TEST_F(BrakeControlTest, PressWhileBrakingSpinsBackUp) {
    ControlObject::set(key("brake_time"), 0.4);
    ControlObject::set(key("softstart_time"), 0.4);
    ControlObject::set(key("play"), 1.0);
    press();
    // Let it slow down to about half speed
    QElapsedTimer timer;
    timer.start();
    while (timer.elapsed() < 200) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 5);
        QThread::msleep(1);
    }
    const double halfway = get("scratch2");
    EXPECT_LT(halfway, 0.9);
    EXPECT_GT(halfway, 0.1);

    press(); // changed my mind: back up
    EXPECT_EQ(1.0, get("brake_active"));
    const auto rates = waitUntilDone();
    EXPECT_EQ(1.0, get("play"));
    EXPECT_EQ(0.0, get("scratch2_enable"));
    // Spins up from where the brake was, not from zero
    ASSERT_FALSE(rates.empty());
    EXPECT_GE(rates.front(), halfway - 0.05);
}

TEST_F(BrakeControlTest, StoppingTheDeckCancels) {
    ControlObject::set(key("brake_time"), 10.0);
    ControlObject::set(key("play"), 1.0);
    press();
    ControlObject::set(key("play"), 0.0);
    waitUntilDone();
    EXPECT_EQ(0.0, get("brake_active"));
    EXPECT_EQ(0.0, get("scratch2_enable"));
}

TEST_F(BrakeControlTest, NothingWithoutTrack) {
    ControlObject::set(key("track_loaded"), 0.0);
    press();
    EXPECT_EQ(0.0, get("brake_active"));
    EXPECT_EQ(0.0, get("play"));
}

} // namespace
