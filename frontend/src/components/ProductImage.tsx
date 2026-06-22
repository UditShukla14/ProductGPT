import { ImageOff } from "lucide-react"

import { cn } from "@/lib/utils"

interface ProductImageProps {
  src?: string | null
  alt: string
  className?: string
  imageClassName?: string
}

export function ProductImage({ src, alt, className, imageClassName }: ProductImageProps) {
  if (!src) {
    return (
      <div
        className={cn(
          "flex h-full w-full items-center justify-center bg-muted/40 text-muted-foreground",
          className
        )}
        aria-hidden
      >
        <ImageOff className="size-8 opacity-40" />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      className={cn("h-full w-full object-contain", imageClassName)}
    />
  )
}
