#pragma once

#include <QList>
#include <QObject>
#include <QString>

#include "preferences/usersettings.h"
#include "track/trackid.h"

class TrackCollection;

/// One playlist per folder: after every library scan, each folder directly
/// inside a library root folder (e.g. Music/stemprep/Downloads/130 fweak)
/// gets a playlist with that name holding all tracks below it.
///
/// Order: the folder's "<name>.m3u8" if there is one (stemprep writes it in
/// Spotify order), otherwise by file name. The playlists are kept in sync on
/// each scan (tracks added and removed) and locked, because they are
/// rewritten; make your own playlists to arrange tracks differently.
///
/// [Library],FolderPlaylists = 0 turns it off.
class FolderPlaylists : public QObject {
    Q_OBJECT
  public:
    FolderPlaylists(TrackCollection* pTrackCollection,
            UserSettingsPointer pConfig,
            QObject* pParent);

  public slots:
    void sync();

  private:
    /// Tracks below folder in playlist order.
    QList<TrackId> tracksInFolder(const QString& folder) const;
    void syncPlaylist(const QString& name, const QList<TrackId>& trackIds);

    TrackCollection* const m_pTrackCollection;
    const UserSettingsPointer m_pConfig;
};
