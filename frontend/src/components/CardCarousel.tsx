import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface CardCarouselProps {
  children: ReactNode
  className?: string
  slideClassName?: string
  ariaLabel?: string
}

export function CardCarousel({
  children,
  className,
  slideClassName = "w-full shrink-0 basis-full snap-start",
  ariaLabel = "Card carousel",
}: CardCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollState = useCallback(() => {
    const track = trackRef.current
    if (!track) return

    const maxScroll = track.scrollWidth - track.clientWidth
    setCanScrollLeft(track.scrollLeft > 8)
    setCanScrollRight(track.scrollLeft < maxScroll - 8)
  }, [])

  useEffect(() => {
    const track = trackRef.current
    if (!track) return

    updateScrollState()
    track.addEventListener("scroll", updateScrollState, { passive: true })
    const observer = new ResizeObserver(updateScrollState)
    observer.observe(track)

    return () => {
      track.removeEventListener("scroll", updateScrollState)
      observer.disconnect()
    }
  }, [children, updateScrollState])

  function scrollByDirection(direction: "left" | "right") {
    const track = trackRef.current
    if (!track) return

    track.scrollBy({
      left: direction === "left" ? -track.clientWidth : track.clientWidth,
      behavior: "smooth",
    })
  }

  const slides = Array.isArray(children) ? children : [children]

  return (
    <div className={cn("relative w-full min-w-0 max-w-full overflow-hidden", className)}>
      {canScrollLeft && (
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Scroll carousel left"
          onClick={() => scrollByDirection("left")}
          className="absolute top-1/2 left-1 z-10 hidden size-8 -translate-y-1/2 rounded-full bg-background shadow-md sm:inline-flex"
        >
          <ChevronLeft className="size-4" />
        </Button>
      )}

      {canScrollRight && (
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Scroll carousel right"
          onClick={() => scrollByDirection("right")}
          className="absolute top-1/2 right-1 z-10 hidden size-8 -translate-y-1/2 rounded-full bg-background shadow-md sm:inline-flex"
        >
          <ChevronRight className="size-4" />
        </Button>
      )}

      <div
        ref={trackRef}
        role="region"
        aria-label={ariaLabel}
        className="flex w-full min-w-0 gap-3 overflow-x-auto overscroll-x-contain scroll-smooth pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden snap-x snap-mandatory"
      >
        {slides.map((slide, index) => (
          <div key={index} className={cn("min-w-0", slideClassName)}>
            {slide}
          </div>
        ))}
      </div>
    </div>
  )
}
