#pragma once

#include <QColor>
#include <QString>
#include <vector>

#include "rendergraph/geometrynode.h"
#include "util/class.h"
#include "waveform/renderers/waveformrendererabstract.h"

class QDomNode;
class SkinContext;

namespace allshader {
class WaveformRenderBeat;
} // namespace allshader

class allshader::WaveformRenderBeat final
        : public QObject,
          public ::WaveformRendererAbstract,
          public rendergraph::GeometryNode {
    Q_OBJECT
  public:
    explicit WaveformRenderBeat(WaveformWidgetRenderer* waveformWidget,
            ::WaveformRendererAbstract::PositionSource type =
                    ::WaveformRendererAbstract::Play);

    // Pure virtual from WaveformRendererAbstract, not used
    void draw(QPainter* painter, QPaintEvent* event) override final;

    void setup(const QDomNode& node, const SkinContext& skinContext) override;

    // Virtuals for rendergraph::Node
    void preprocess() override;

  public slots:
    void setColor(const QColor& color) {
        m_color = color;
    }

  private:
    QColor m_color;
    // Colors used when the track has bar/phrase data (TrackStructure)
    QColor m_barColor;
    QColor m_phraseColor;
    bool m_isSlipRenderer;

    /// A section name drawn above the section strip. The child nodes are
    /// created once and hidden (no vertices) when not needed, so the node
    /// tree never changes while rendering.
    struct SectionLabel {
        rendergraph::GeometryNode* pNode = nullptr;
        QString textureKey;
        float width = 0;
        float height = 0;
    };
    std::vector<SectionLabel> m_sectionLabels;

    bool preprocessInner();
    struct SectionSpanOnScreen {
        int index;
        float x1;
        float x2;
        QString label;
        QColor color;
    };
    void updateSectionLabels(const std::vector<SectionSpanOnScreen>& sections, float bottom);
    void hideSectionLabels();

    DISALLOW_COPY_AND_ASSIGN(WaveformRenderBeat);
};
