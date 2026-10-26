#include "library/folderplaylists.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QSqlError>
#include <QSqlQuery>
#include <QTextStream>
#include <algorithm>
#include <limits>
#include <utility>

#include "library/dao/playlistdao.h"
#include "library/trackcollection.h"
#include "moc_folderplaylists.cpp"
#include "util/logger.h"

namespace {

const mixxx::Logger kLogger("FolderPlaylists");

const ConfigKey kEnabledKey(QStringLiteral("[Library]"), QStringLiteral("FolderPlaylists"));

/// For SQL LIKE with ESCAPE '\'
QString escapeLike(QString text) {
    text.replace(QChar('\\'), QStringLiteral("\\\\"));
    text.replace(QChar('%'), QStringLiteral("\\%"));
    text.replace(QChar('_'), QStringLiteral("\\_"));
    return text;
}

/// Lowercase absolute paths listed in an .m3u/.m3u8 file, in order.
QHash<QString, int> playlistOrder(const QString& m3uPath) {
    QHash<QString, int> order;
    QFile file(m3uPath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return order;
    }
    const QDir base = QFileInfo(m3uPath).absoluteDir();
    QTextStream in(&file);
    in.setEncoding(QStringConverter::Utf8);
    int index = 0;
    while (!in.atEnd()) {
        const QString line = in.readLine().trimmed();
        if (line.isEmpty() || line.startsWith(QChar('#'))) {
            continue;
        }
        const QString path = QDir::cleanPath(base.absoluteFilePath(line)).toLower();
        if (!order.contains(path)) {
            order.insert(path, index++);
        }
    }
    return order;
}

} // namespace

FolderPlaylists::FolderPlaylists(TrackCollection* pTrackCollection,
        UserSettingsPointer pConfig,
        QObject* pParent)
        : QObject(pParent),
          m_pTrackCollection(pTrackCollection),
          m_pConfig(std::move(pConfig)) {
}

void FolderPlaylists::sync() {
    if (!m_pConfig->getValue(kEnabledKey, true)) {
        return;
    }
    const QStringList roots = m_pTrackCollection->getDirectoryDAO().getRootDirStrings();
    for (const QString& root : roots) {
        const auto folders = QDir(root).entryInfoList(
                QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name | QDir::IgnoreCase);
        for (const QFileInfo& folder : folders) {
            if (folder.fileName().startsWith(QChar('.'))) {
                continue; // e.g. stemprep's .stemprep cache folders
            }
            const QList<TrackId> trackIds = tracksInFolder(folder.absoluteFilePath());
            if (!trackIds.isEmpty()) {
                syncPlaylist(folder.fileName(), trackIds);
            }
        }
    }
}

QList<TrackId> FolderPlaylists::tracksInFolder(const QString& folder) const {
    const QString prefix = QDir::fromNativeSeparators(QDir::cleanPath(folder)) + QChar('/');
    QSqlQuery query(m_pTrackCollection->database());
    query.prepare(QStringLiteral(
            "SELECT library.id, track_locations.location FROM library "
            "INNER JOIN track_locations ON library.location = track_locations.id "
            "WHERE library.mixxx_deleted = 0 AND track_locations.fs_deleted = 0 "
            "AND track_locations.location LIKE :prefix ESCAPE '\\'"));
    query.bindValue(QStringLiteral(":prefix"), escapeLike(prefix) + QChar('%'));
    if (!query.exec()) {
        kLogger.warning() << "Query failed for" << folder << query.lastError();
        return {};
    }
    struct Entry {
        TrackId id;
        QString location;
        int order;
    };
    const QString folderName = QFileInfo(folder).fileName();
    const QHash<QString, int> order = playlistOrder(
            QDir(folder).absoluteFilePath(folderName + QStringLiteral(".m3u8")));
    QList<Entry> entries;
    while (query.next()) {
        const QString location = query.value(1).toString();
        entries.append({TrackId(query.value(0)),
                location,
                order.value(QDir::cleanPath(location).toLower(), std::numeric_limits<int>::max())});
    }
    std::sort(entries.begin(), entries.end(), [](const Entry& a, const Entry& b) {
        if (a.order != b.order) {
            return a.order < b.order;
        }
        return QString::compare(a.location, b.location, Qt::CaseInsensitive) < 0;
    });
    QList<TrackId> ids;
    ids.reserve(entries.size());
    for (const auto& entry : entries) {
        ids.append(entry.id);
    }
    return ids;
}

void FolderPlaylists::syncPlaylist(const QString& name, const QList<TrackId>& trackIds) {
    PlaylistDAO& playlists = m_pTrackCollection->getPlaylistDAO();
    int playlistId = playlists.getPlaylistIdFromName(name);
    if (playlistId == kInvalidPlaylistId) {
        playlistId = playlists.createPlaylist(name);
        if (playlistId == kInvalidPlaylistId) {
            kLogger.warning() << "Could not create playlist" << name;
            return;
        }
        kLogger.info() << "Created playlist" << name << "for its folder";
    }
    if (playlists.getTrackIdsInPlaylistOrder(playlistId) != trackIds) {
        const bool locked = playlists.isPlaylistLocked(playlistId);
        if (locked) {
            playlists.setPlaylistLocked(playlistId, false);
        }
        QList<int> positions;
        const int count = playlists.getMaxPosition(playlistId);
        for (int position = 1; position <= count; ++position) {
            positions.append(position);
        }
        if (!positions.isEmpty()) {
            playlists.removeTracksFromPlaylist(playlistId, positions);
        }
        playlists.appendTracksToPlaylist(trackIds, playlistId);
        kLogger.info() << "Playlist" << name << "now has" << trackIds.size() << "tracks";
    }
    if (!playlists.isPlaylistLocked(playlistId)) {
        playlists.setPlaylistLocked(playlistId, true);
    }
}
