'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'
import mermaid from 'mermaid'
import { MermaidDiagram } from '../types'
import { Button } from './ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/card'
import { Skeleton } from './ui/skeleton'

interface MermaidDiagramRendererProps {
  diagrams: MermaidDiagram[]
  alignment?: 'left' | 'center' | 'right'
}

export default function MermaidDiagramRenderer({ diagrams, alignment = 'center' }: MermaidDiagramRendererProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const diagramRef = useRef<HTMLDivElement>(null)
  const modalDiagramRef = useRef<HTMLDivElement>(null)
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const initMermaid = async () => {
      try {
        await mermaid.initialize({ startOnLoad: false, theme: 'base', })
        setIsLoading(false)
      } catch (err) {
        console.error('Error initializing mermaid:', err)
        setError('Failed to initialize diagram renderer.')
        setIsLoading(false)
      }
    }
    initMermaid()
  }, [])

  useEffect(() => {
    if (!isLoading) {
      renderDiagram()
    }
  }, [currentIndex, diagrams, alignment, isLoading])

  const renderDiagram = async (modalRef?: React.RefObject<HTMLDivElement>) => {
    const element = modalRef ? modalRef.current : diagramRef.current
    if (!element) return

    try {
      setIsLoading(true)
      const { svg } = await mermaid.render(`mermaid-diagram-${currentIndex}${modalRef ? '-modal' : ''}`, diagrams[currentIndex].diagram)
      element.innerHTML = svg
      applyAlignment(element)
      setError(null)
    } catch (err) {
      console.error('Error rendering diagram:', err)
      setError('Failed to render diagram. Please check the diagram syntax.')
    } finally {
      setIsLoading(false)
    }
  }

  const applyAlignment = (element: HTMLDivElement) => {
    const svgElement = element.querySelector('svg')
    if (svgElement) {
      svgElement.style.display = 'block'
      svgElement.style.margin = alignment === 'center' ? 'auto' : alignment === 'right' ? '0 0 0 auto' : '0'
    }
  }

  const scrollToTop = () => {
    if (cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleNext = useCallback(() => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % diagrams.length)
    setTimeout(scrollToTop, 0)
  }, [diagrams.length, scrollToTop])

  const handlePrevious = useCallback(() => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + diagrams.length) % diagrams.length)
    setTimeout(scrollToTop, 0)
  }, [diagrams.length, scrollToTop])

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true)
  }, [])

  useEffect(() => {
    if (isModalOpen) {
      // Delay rendering the diagram in the modal
      const timer = setTimeout(() => renderDiagram(modalDiagramRef), 100)
      return () => clearTimeout(timer)
    }
  }, [isModalOpen, currentIndex])

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      handleNext()
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      handlePrevious()
    } else if (event.key === 'Enter' || event.key === ' ') {
      handleOpenModal()
    } else if (event.key === 'Escape' && isModalOpen) {
      setIsModalOpen(false)
    }
  }, [handleNext, handlePrevious, handleOpenModal, isModalOpen])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown])

  return (
    <>
      <Card className="w-full max-w-7xl mx-auto" ref={cardRef} tabIndex={0}>
        <CardHeader>
          <CardTitle>{diagrams[currentIndex].question}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="w-full h-64" />
          ) : error ? (
            <div className="text-red-500">{error}</div>
          ) : (
            <div
              ref={diagramRef}
              className="mermaid-diagram cursor-pointer"
              aria-label={`Reasoning Diagram ${currentIndex + 1} of ${diagrams.length}. Click to enlarge.`}
              key={`diagram-${currentIndex}`}
            />
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button onClick={handlePrevious} disabled={diagrams.length <= 1 || isLoading}>
            Previous
          </Button>
          <div className="text-sm text-muted-foreground">
            Diagram {currentIndex + 1} of {diagrams.length}
          </div>
          <Button onClick={handleNext} disabled={diagrams.length <= 1 || isLoading}>
            Next
          </Button>
        </CardFooter>
      </Card>
    </>
  )
}