'use client'

import React, { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'
import { MermaidDiagram } from '../types'
import { Button } from './ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/card'
import { Skeleton } from './ui/skeleton'
import { Dialog, DialogContent, DialogClose } from './ui/dialog'
import { X } from 'lucide-react'

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
        await mermaid.initialize({ startOnLoad: false })
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

  const handleNext = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % diagrams.length)
    setTimeout(scrollToTop, 0)
  }

  const handlePrevious = () => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + diagrams.length) % diagrams.length)
    setTimeout(scrollToTop, 0)
  }

  const handleOpenModal = () => {
    setIsModalOpen(true)
    setTimeout(() => renderDiagram(modalDiagramRef), 0)
  }

  return (
    <>
      <Card className="w-full max-w-3xl mx-auto" ref={cardRef}>
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
              onClick={handleOpenModal}
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

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] overflow-auto">
          <DialogClose className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
            <X className="h-4 w-4 text-black" />
            <span className="sr-only">Close</span>
          </DialogClose>
          <div
            ref={modalDiagramRef}
            className="mermaid-diagram-modal"
            aria-label={`Enlarged Reasoning Diagram ${currentIndex + 1} of ${diagrams.length}`}
          />
        </DialogContent>
      </Dialog>
    </>
  )
}