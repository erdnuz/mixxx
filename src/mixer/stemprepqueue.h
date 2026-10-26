#pragma once

#include <QString>

#include "preferences/usersettings.h"

/// Asks the external stemprep tool (tools/stemprep) to make stems and a
/// bars/phrases/sections analysis for a track, in the background.
///
/// Requests are small JSON files in <stemprep data dir>/queue, picked up by
/// `stemprep worker`, which is started here when it isn't running. The
/// worker writes "<track>.structure.json" next to the track; that file
/// links the stem file Mixxx then plays (see SoundSourceProxy::forDecoding()).
///
/// Settings ([Structure] group):
///   AutoStems     1 (default) to send loaded tracks to stemprep, 0 to not
///   StemprepPath  the stemprep executable (default: the Windows install in
///                 %LOCALAPPDATA%\stemprep\venv\Scripts\stemprep.exe)
class StemprepQueue {
  public:
    /// Lower numbers are done first. Tracks loaded into a deck come first.
    static constexpr int kPriorityDeck = 0;

    /// Queue the track unless it already has high quality stems. Does
    /// nothing if stemprep isn't installed or AutoStems is off.
    static void request(const QString& trackLocation, int priority, UserSettingsPointer pConfig);

    /// <stemprep data dir>/queue
    static QString queueDir();

  private:
    static QString dataDir();
    static QString stemprepPath(const UserSettingsPointer& pConfig);
    static void ensureWorkerRunning(const QString& stemprepPath);
};
