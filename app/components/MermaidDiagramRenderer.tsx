import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramRendererProps {
  diagrams: string[];
}

const MermaidDiagramRenderer: React.FC<MermaidDiagramRendererProps> = ({ diagrams }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const diagramRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    mermaid.initialize({ startOnLoad: true });
    const element = diagramRef.current;
    if (element) {
      mermaid.render(`mermaid-diagram-${currentIndex}`, diagrams[currentIndex]).then(({ svg }) => {
        element.innerHTML = svg;
      });
    }
  }, [diagrams, currentIndex]);

  const handleClick = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % diagrams.length);
  };

  return (
    <div className="mermaid-diagrams">
      <div
        ref={diagramRef}
        className="mermaid-diagram content-center"
        onClick={handleClick}
        style={{ cursor: 'pointer' }}
      />
      <p className="text-xs text-gray-500">Reasoning Diagram {currentIndex + 1} of {diagrams.length}. Click to see more.</p>
    </div>
  );
};

export default MermaidDiagramRenderer;