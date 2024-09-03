import React, { useLayoutEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramRendererProps {
  diagrams: string[];
  alignment?: 'left' | 'center' | 'right';
}

const MermaidDiagramRenderer: React.FC<MermaidDiagramRendererProps> = ({ diagrams, alignment = 'center' }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const diagramRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    mermaid.initialize({ startOnLoad: false });
    const renderDiagram = () => {
      const element = diagramRef.current;
      if (element) {
        mermaid.render(`mermaid-diagram-${currentIndex}`, diagrams[currentIndex]).then(({ svg }) => {
          element.innerHTML = svg;
          // Apply alignment to the rendered SVG
          const svgElement = element.querySelector('svg');
          if (svgElement) {
            svgElement.style.display = 'block';
            svgElement.style.margin = alignment === 'center' ? 'auto' : alignment === 'right' ? '0 0 0 auto' : '0';
          }
        });
      }
    };

    // Add a small delay to ensure mermaid is fully initialized
    setTimeout(renderDiagram, 40);
  }, [currentIndex, diagrams]);

  const handleClick = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % diagrams.length);
  };

  return (
    <div className="mermaid-diagrams">
      <div
        ref={diagramRef}
        className="mermaid-diagram"
        onClick={handleClick}
        style={{ cursor: 'pointer' }}
      />
      <p className="text-xs text-gray-500 text-center">Reasoning Diagram {currentIndex + 1} of {diagrams.length}. Click to see more.</p>
    </div>
  );
};

export default MermaidDiagramRenderer;