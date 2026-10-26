#include "mixer/stemprepqueue.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSaveFile>
#include <QStandardPaths>

#include "track/trackstructure.h"
#include "util/logger.h"

namespace {

const mixxx::Logger kLogger("StemprepQueue");

const QString kConfigGroup = QStringLiteral("[Structure]");
const QString kAutoStemsKey = QStringLiteral("AutoStems");
const QString kStemprepPathKey = QStringLiteral("StemprepPath");
// The worker refreshes this file while it runs (see stemprep/worker.py)
const QString kWorkerLockName = QStringLiteral("worker.lock");
constexpr qint64 kWorkerStaleSeconds = 60;

/// True if the sidecar already links stems that won't be replaced.
bool hasFinalStems(const QString& trackLocation) {
    QFile file(mixxx::TrackStructure::sidecarPath(trackLocation));
    if (!file.open(QIODevice::ReadOnly)) {
        return false;
    }
    const QJsonObject root = QJsonDocument::fromJson(file.readAll()).object();
    const QString stems = root.value(QStringLiteral("stems")).toString();
    return !stems.isEmpty() && QFileInfo(stems).isFile() &&
            root.value(QStringLiteral("stems_quality")).toString() != QStringLiteral("fast");
}

} // namespace

// static
QString StemprepQueue::dataDir() {
#ifdef Q_OS_WIN
    const QString localAppData = qEnvironmentVariable("LOCALAPPDATA");
    if (!localAppData.isEmpty()) {
        return QDir(localAppData).filePath(QStringLiteral("stemprep"));
    }
#endif
    return QDir(QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation))
            .filePath(QStringLiteral("stemprep"));
}

// static
QString StemprepQueue::queueDir() {
    return QDir(dataDir()).filePath(QStringLiteral("queue"));
}

// static
QString StemprepQueue::stemprepPath(const UserSettingsPointer& pConfig) {
    const QString configured = pConfig->getValue(ConfigKey(kConfigGroup, kStemprepPathKey));
    if (!configured.isEmpty()) {
        return configured;
    }
#ifdef Q_OS_WIN
    return QDir(dataDir()).filePath(QStringLiteral("venv/Scripts/stemprep.exe"));
#else
    return QDir(dataDir()).filePath(QStringLiteral("venv/bin/stemprep"));
#endif
}

// static
void StemprepQueue::request(
        const QString& trackLocation, int priority, UserSettingsPointer pConfig) {
    if (trackLocation.isEmpty() ||
            !pConfig->getValue(ConfigKey(kConfigGroup, kAutoStemsKey), true)) {
        return;
    }
    const QString exe = stemprepPath(pConfig);
    if (!QFileInfo(exe).isExecutable()) {
        return; // stemprep not installed
    }
    if (hasFinalStems(trackLocation)) {
        return;
    }
    if (!QDir().mkpath(queueDir())) {
        kLogger.warning() << "Cannot create" << queueDir();
        return;
    }
    // One file per track: requesting it again only updates the priority
    const QString name = QString::fromLatin1(
            QCryptographicHash::hash(trackLocation.toUtf8(), QCryptographicHash::Sha1)
                    .toHex());
    QSaveFile out(QDir(queueDir()).filePath(name + QStringLiteral(".json")));
    if (!out.open(QIODevice::WriteOnly)) {
        kLogger.warning() << "Cannot write stemprep request for" << trackLocation;
        return;
    }
    QJsonObject request;
    request.insert(QStringLiteral("path"), QDir::toNativeSeparators(trackLocation));
    request.insert(QStringLiteral("priority"), priority);
    request.insert(QStringLiteral("requested"),
            QDateTime::currentDateTimeUtc().toString(Qt::ISODate));
    out.write(QJsonDocument(request).toJson(QJsonDocument::Compact));
    if (!out.commit()) {
        kLogger.warning() << "Cannot write stemprep request for" << trackLocation;
        return;
    }
    kLogger.info() << "Asked stemprep for stems of" << trackLocation;
    ensureWorkerRunning(exe);
}

// static
void StemprepQueue::ensureWorkerRunning(const QString& stemprepPath) {
    const QFileInfo lock(QDir(dataDir()).filePath(kWorkerLockName));
    if (lock.exists() &&
            lock.lastModified().secsTo(QDateTime::currentDateTime()) < kWorkerStaleSeconds) {
        return; // running
    }
    // The worker runs at low priority and exits when the queue stays empty.
    // On Windows stemprep.exe is a console program: start it through the
    // venv's pythonw.exe instead so no console window pops up while mixing.
    QString program = stemprepPath;
    QStringList args = {QStringLiteral("worker")};
#ifdef Q_OS_WIN
    const QString pythonw = QFileInfo(stemprepPath).dir().filePath(QStringLiteral("pythonw.exe"));
    if (QFileInfo::exists(pythonw)) {
        program = pythonw;
        args = {QStringLiteral("-m"), QStringLiteral("stemprep"), QStringLiteral("worker")};
    }
#endif
    if (QProcess::startDetached(program, args)) {
        kLogger.info() << "Started stemprep worker:" << program << args;
    } else {
        kLogger.warning() << "Could not start stemprep worker:" << program << args;
    }
}
