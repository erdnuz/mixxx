#include "waveform/renderers/allshader/waveformrenderbeat.h"

#include <QDomNode>
#include <QFont>
#include <QFontMetricsF>
#include <QImage>
#include <QPainter>
#include <QVector4D>
#include <algorithm>
#include <cmath>

#include "engine/engine.h"
#include "moc_waveformrenderbeat.cpp"
#include "rendergraph/geometry.h"
#include "rendergraph/material/rgbamaterial.h"
#include "rendergraph/material/texturematerial.h"
#include "rendergraph/texture.h"
#include "rendergraph/vertexupdaters/rgbavertexupdater.h"
#include "rendergraph/vertexupdaters/texturedvertexupdater.h"
#include "skin/legacy/skincontext.h"
#include "track/track.h"
#include "track/trackstructure.h"
#include "util/colorcomponents.h"
#include "waveform/renderers/waveformwidgetrenderer.h"
#include "waveform/waveform.h"
#include "waveform/waveformwidgetfactory.h"
#include "widget/wskincolor.h"

using namespace rendergraph;

namespace {

// Phrase lines that don't start a new section (e.g. every 8 bars inside a
// long drop) use this color unless the skin sets <PhraseColor>.
const QColor kDefaultPhraseColor = QColor(0xFF, 0xB0, 0x00);

// Section names visible at the same time (sections are at least 4 bars long,
// so only a few fit on screen even when zoomed out).
constexpr int kMaxSectionLabels = 6;

QVector4D toVec(const QColor& color, float alphaScale) {
    float r, g, b, a;
    getRgbF(color, &r, &g, &b, &a);
    return {r, g, b, std::clamp(a * alphaScale, 0.f, 1.f)};
}

// Same look as the section names on the overview: bold name on the
// section color. Drawn once per name with QPainter into a texture.
QImage makeSectionLabelImage(const QString& text, const QColor& color, float devicePixelRatio) {
    QFont font;
    font.setPixelSize(10);
    font.setBold(true);
    const QFontMetricsF metrics(font);
    const float width = std::ceil(static_cast<float>(metrics.horizontalAdvance(text))) + 8.f;
    const float height = std::ceil(static_cast<float>(metrics.height())) + 2.f;
    QImage image(QSize(static_cast<int>(std::lround(width * devicePixelRatio)),
                         static_cast<int>(std::lround(height * devicePixelRatio))),
            QImage::Format_ARGB32_Premultiplied);
    if (image.isNull()) {
        return image;
    }
    image.setDevicePixelRatio(devicePixelRatio);
    image.fill(Qt::transparent);

    QPainter painter(&image);
    painter.setRenderHint(QPainter::Antialiasing);
    QColor background = color;
    background.setAlphaF(0.85f);
    painter.setPen(Qt::NoPen);
    painter.setBrush(background);
    painter.drawRoundedRect(QRectF(0, 0, width, height), 3, 3);
    painter.setFont(font);
    painter.setPen(color.lightnessF() > 0.6 ? Qt::black : Qt::white);
    painter.drawText(QRectF(0, 0, width, height), Qt::AlignCenter, text);
    painter.end();
    return image;
}

} // namespace

namespace allshader {

WaveformRenderBeat::WaveformRenderBeat(WaveformWidgetRenderer* waveformWidget,
        ::WaveformRendererAbstract::PositionSource type)
        : ::WaveformRendererAbstract(waveformWidget),
          m_isSlipRenderer(type == ::WaveformRendererAbstract::Slip) {
    initForRectangles<RGBAMaterial>(0);
    setUsePreprocess(true);
    if (!m_isSlipRenderer) {
        for (int i = 0; i < kMaxSectionLabels; ++i) {
            auto pNode = std::make_unique<GeometryNode>();
            pNode->initForRectangles<TextureMaterial>(0);
            SectionLabel label;
            label.pNode = appendChildNode(std::move(pNode));
            m_sectionLabels.push_back(label);
        }
    }
}

void WaveformRenderBeat::setup(const QDomNode& node, const SkinContext& skinContext) {
    m_color = QColor(skinContext.selectString(node, QStringLiteral("BeatColor")));
    m_color = WSkinColor::getCorrectColor(m_color).toRgb();

    const QString barColorName = skinContext.selectString(node, QStringLiteral("BarColor"));
    m_barColor = barColorName.isEmpty() ? m_color : QColor(barColorName);
    if (!m_barColor.isValid()) {
        m_barColor = m_color;
    }
    m_barColor = WSkinColor::getCorrectColor(m_barColor).toRgb();

    const QString phraseColorName = skinContext.selectString(node, QStringLiteral("PhraseColor"));
    m_phraseColor = phraseColorName.isEmpty() ? kDefaultPhraseColor : QColor(phraseColorName);
    if (!m_phraseColor.isValid()) {
        m_phraseColor = kDefaultPhraseColor;
    }
    m_phraseColor = WSkinColor::getCorrectColor(m_phraseColor).toRgb();
}

void WaveformRenderBeat::draw(QPainter* painter, QPaintEvent* event) {
    Q_UNUSED(painter);
    Q_UNUSED(event);
    DEBUG_ASSERT(false);
}

void WaveformRenderBeat::preprocess() {
    if (!preprocessInner()) {
        geometry().allocate(0);
        markDirtyGeometry();
        hideSectionLabels();
    }
}

void WaveformRenderBeat::hideSectionLabels() {
    for (auto& label : m_sectionLabels) {
        if (label.pNode->geometry().vertexCount() > 0) {
            label.pNode->geometry().allocate(0);
            label.pNode->markDirtyGeometry();
        }
    }
}

void WaveformRenderBeat::updateSectionLabels(
        const std::vector<SectionSpanOnScreen>& sections, float bottom) {
    const float devicePixelRatio = m_waveformRenderer->getDevicePixelRatio();
    const auto roundToPixel = [devicePixelRatio](float v) {
        return std::round(v * devicePixelRatio) / devicePixelRatio;
    };
    // Each section always uses the same node (index modulo pool size), so a
    // label's texture is only redrawn when a far-away section takes it over.
    std::vector<bool> shown(m_sectionLabels.size(), false);
    for (const auto& section : sections) {
        const size_t slot = static_cast<size_t>(section.index) % m_sectionLabels.size();
        if (shown[slot]) {
            continue; // more sections on screen than nodes
        }
        auto& label = m_sectionLabels[slot];
        const QString text = section.label.toUpper();
        const QString key = text + section.color.name(QColor::HexArgb) +
                QString::number(devicePixelRatio);
        if (label.textureKey != key) {
            const QImage image = makeSectionLabelImage(text, section.color, devicePixelRatio);
            if (image.isNull()) {
                continue;
            }
            dynamic_cast<TextureMaterial&>(label.pNode->material())
                    .setTexture(std::make_unique<Texture>(
                            m_waveformRenderer->getContext(), image));
            label.pNode->markDirtyMaterial();
            label.textureKey = key;
            label.width = image.width() / devicePixelRatio;
            label.height = image.height() / devicePixelRatio;
        }
        // Only where the visible part of the section is wide enough
        if (section.x2 - section.x1 < label.width + 4.f) {
            continue;
        }
        // At the section start; while the start has scrolled past the left
        // edge, the name stays at the edge so the current section is named.
        const float x = roundToPixel(std::max(section.x1, 0.f) + 2.f);
        const float y = roundToPixel(bottom - label.height - 2.f);
        label.pNode->geometry().allocate(6);
        TexturedVertexUpdater vertexUpdater{
                label.pNode->geometry().vertexDataAs<Geometry::TexturedPoint2D>()};
        vertexUpdater.addRectangle({x, y}, {x + label.width, y + label.height}, {0.f, 0.f}, {1.f, 1.f});
        label.pNode->markDirtyGeometry();
        shown[slot] = true;
    }
    for (size_t slot = 0; slot < m_sectionLabels.size(); ++slot) {
        auto& label = m_sectionLabels[slot];
        if (!shown[slot] && label.pNode->geometry().vertexCount() > 0) {
            label.pNode->geometry().allocate(0);
            label.pNode->markDirtyGeometry();
        }
    }
}

bool WaveformRenderBeat::preprocessInner() {
    const TrackPointer trackInfo = m_waveformRenderer->getTrackInfo();

    if (!trackInfo || (m_isSlipRenderer && !m_waveformRenderer->isSlipActive())) {
        return false;
    }

    const bool isStemTrack = trackInfo && trackInfo->hasStem() &&
            trackInfo->getWaveform() && trackInfo->getWaveform()->hasStem();
    const bool splitStemTracks = isStemTrack &&
            WaveformWidgetFactory::instance()->isStemSplitTracks();

    auto positionType = m_isSlipRenderer ? ::WaveformRendererAbstract::Slip
                                         : ::WaveformRendererAbstract::Play;

    mixxx::BeatsPointer trackBeats = trackInfo->getBeats();
    if (!trackBeats) {
        return false;
    }

    const int alpha = m_waveformRenderer->getBeatGridAlpha();
    if (alpha == 0) {
        return false;
    }
    const float alphaF = alpha / 100.0f;

    const float devicePixelRatio = m_waveformRenderer->getDevicePixelRatio();

    const double trackSamples = m_waveformRenderer->getTrackSamples();
    if (trackSamples <= 0.0) {
        return false;
    }

    const double firstDisplayedPosition =
            m_waveformRenderer->getFirstDisplayedPosition(positionType);
    const double lastDisplayedPosition =
            m_waveformRenderer->getLastDisplayedPosition(positionType);

    const auto startPosition = mixxx::audio::FramePos::fromEngineSamplePos(
            firstDisplayedPosition * trackSamples);
    const auto endPosition = mixxx::audio::FramePos::fromEngineSamplePos(
            lastDisplayedPosition * trackSamples);

    if (!startPosition.isValid() || !endPosition.isValid()) {
        return false;
    }

    // Bars/phrases/sections, if the track has a structure file and the
    // detected downbeats agree with this beat grid.
    std::shared_ptr<const mixxx::TrackStructure::Alignment> pAlignment;
    if (const auto pStructure = trackInfo->getStructure()) {
        pAlignment = pStructure->alignTo(trackBeats);
        if (pAlignment && pAlignment->confidence < 0.5) {
            pAlignment.reset();
        }
    }

    const float rendererBreadth = m_waveformRenderer->getBreadth();

    const int numVerticesPerLine = 6; // 2 triangles

    // Count the number of beats in the range to reserve space in the vertex
    // buffer. Note that we could also use
    //   int numBearsInRange = trackBeats->numBeatsInRange(startPosition, endPosition);
    // for this, but there have been reports of that method failing with a DEBUG_ASSERT.
    int numBeatsInRange = 0;
    for (auto it = trackBeats->iteratorFrom(startPosition);
            it != trackBeats->cend() && *it <= endPosition;
            ++it) {
        numBeatsInRange++;
    }

    const int numBoxesPerBeat = (m_isSlipRenderer && splitStemTracks)
            ? mixxx::kMaxSupportedStems
            : 1;
    // One extra rectangle per section for the colored strip at the bottom.
    int numSectionBoxes = 0;
    if (pAlignment && !m_isSlipRenderer) {
        numSectionBoxes = static_cast<int>(pAlignment->sections.size());
    }
    const int reserved = numBeatsInRange * numVerticesPerLine * numBoxesPerBeat +
            numSectionBoxes * numVerticesPerLine;
    geometry().allocate(reserved);

    RGBAVertexUpdater vertexUpdater{geometry().vertexDataAs<Geometry::RGBAColoredPoint2D>()};

    const float boxBreadth = splitStemTracks
            ? rendererBreadth / static_cast<float>(mixxx::kMaxSupportedStems)
            : rendererBreadth;

    // With structure data, ordinary beats are drawn fainter so the bars
    // stand out; without it everything looks exactly as before.
    const QVector4D beatColor = toVec(m_color, pAlignment ? alphaF * 0.55f : alphaF);
    const QVector4D barColor = toVec(m_barColor, std::min(1.f, alphaF * 1.6f));
    const QVector4D phraseColor = toVec(m_phraseColor, std::min(1.f, alphaF * 2.f));

    auto it = trackBeats->iteratorFrom(startPosition);
    int beatIndex = pAlignment ? (it - trackBeats->cfirstmarker()) : 0;
    for (; it != trackBeats->cend() && *it <= endPosition; ++it, ++beatIndex) {
        double beatPosition = it->toEngineSamplePos();
        double xBeatPoint =
                m_waveformRenderer->transformSamplePositionInRendererWorld(
                        beatPosition, positionType);

        xBeatPoint = qRound(xBeatPoint * devicePixelRatio) / devicePixelRatio;

        float width = 1.f;
        QVector4D color = beatColor;
        if (pAlignment) {
            if (pAlignment->isPhraseStart(beatIndex)) {
                width = 3.f;
                const auto* pSection = pAlignment->sectionAt(beatIndex);
                color = (pSection && pSection->startBeat == beatIndex && pSection->color.isValid())
                        ? toVec(pSection->color, std::min(1.f, alphaF * 2.f))
                        : phraseColor;
            } else if (pAlignment->isBarStart(beatIndex)) {
                width = 2.f;
                color = barColor;
            }
        }

        const float x1 = static_cast<float>(xBeatPoint) - (width > 1.f ? 1.f : 0.f);
        const float x2 = x1 + width;

        if (m_isSlipRenderer && splitStemTracks) {
            for (int stemIdx = 0; stemIdx < mixxx::kMaxSupportedStems; ++stemIdx) {
                const float posy1 = stemIdx * boxBreadth;
                const float posy2 = posy1 + boxBreadth / 2.f;
                vertexUpdater.addRectangle({x1, posy1}, {x2, posy2}, color);
            }
        } else {
            vertexUpdater.addRectangle({x1, 0.f},
                    {x2, m_isSlipRenderer ? rendererBreadth / 2 : rendererBreadth},
                    color);
        }
    }

    // Section strip along the bottom edge: Intro/Build/Drop/... colors,
    // with the section names just above it.
    if (numSectionBoxes > 0) {
        const float stripHeight = std::max(3.f, rendererBreadth * 0.04f);
        const float y2 = rendererBreadth;
        const float y1 = y2 - stripHeight;
        const float rendererLength = static_cast<float>(m_waveformRenderer->getLength());
        std::vector<SectionSpanOnScreen> onScreen;
        int sectionIndex = -1;
        for (const auto& section : pAlignment->sections) {
            ++sectionIndex;
            const auto start = mixxx::TrackStructure::beatPosition(*trackBeats, section.startBeat);
            const auto end = mixxx::TrackStructure::beatPosition(*trackBeats, section.endBeat);
            float x1 = static_cast<float>(m_waveformRenderer->transformSamplePositionInRendererWorld(
                    start.toEngineSamplePos(), positionType));
            float x2 = static_cast<float>(m_waveformRenderer->transformSamplePositionInRendererWorld(
                    end.toEngineSamplePos(), positionType));
            x1 = std::clamp(x1, 0.f, rendererLength);
            x2 = std::clamp(x2, 0.f, rendererLength);
            if (x2 - x1 < 1.f) {
                // Off screen: still emit a degenerate box to match the
                // reserved vertex count.
                x2 = x1;
            } else if (!section.label.isEmpty()) {
                onScreen.push_back({sectionIndex, x1, x2, section.label, section.color});
            }
            vertexUpdater.addRectangle({x1, y1}, {x2, y2}, toVec(section.color, 0.85f));
        }
        updateSectionLabels(onScreen, y1);
    } else {
        hideSectionLabels();
    }
    markDirtyGeometry();

    DEBUG_ASSERT(reserved == vertexUpdater.index());

    markDirtyMaterial();

    return true;
}

} // namespace allshader
