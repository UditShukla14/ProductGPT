import type { HvacComponent } from "@/types/api"
import { Box, Flame, Snowflake } from "lucide-react"

import { ProductImage } from "@/components/ProductImage"
import { cn } from "@/lib/utils"

const componentIcon: Record<string, React.ReactNode> = {
  outdoor: <Snowflake className="size-3" />,
  coil: <Box className="size-3" />,
  furnace: <Flame className="size-3" />,
}

const componentLabel: Record<string, string> = {
  outdoor: "Outdoor",
  coil: "Coil",
  furnace: "Furnace",
}

interface MatchupComponentImagesProps {
  components: HvacComponent[]
  fallbackImage?: string | null
  fallbackAlt?: string
  className?: string
  compact?: boolean
  spread?: boolean
}

export function MatchupComponentImages({
  components,
  fallbackImage,
  fallbackAlt = "HVAC product",
  className,
  compact = false,
  spread = false,
}: MatchupComponentImagesProps) {
  if (components.length === 0) {
    return (
      <div
        className={cn(
          "flex shrink-0 items-center justify-center border-r bg-muted/20 p-2",
          compact ? "w-20" : "w-24 sm:w-28",
          className
        )}
      >
        <ProductImage
          src={fallbackImage}
          alt={fallbackAlt}
          className="aspect-square w-full"
          imageClassName={compact ? "max-h-16" : "max-h-24"}
        />
      </div>
    )
  }

  const tileWidth = spread ? "min-w-0 flex-1" : compact ? "w-[4.25rem]" : "w-[4.75rem] sm:w-[5.25rem]"

  return (
    <div
      className={cn(
        "flex shrink-0 divide-x bg-muted/20",
        spread ? "w-full border-r-0" : "divide-x border-r",
        className
      )}
    >
      {components.map((component) => (
        <div
          key={`${component.type}-${component.model}`}
          className={cn("flex min-w-0 flex-col", tileWidth)}
        >
          <div className={cn("flex flex-1 items-center justify-center p-1.5", compact ? "min-h-16" : "min-h-20")}>
            <ProductImage
              src={component.image_url}
              alt={component.model}
              className="h-full w-full"
              imageClassName={compact ? "max-h-14 object-contain" : "max-h-20 object-contain"}
            />
          </div>
          <div className="flex items-center justify-center gap-0.5 border-t bg-background/60 px-1 py-1">
            {componentIcon[component.type]}
            <span className="truncate text-[9px] font-medium uppercase tracking-wide text-muted-foreground">
              {componentLabel[component.type] ?? component.type}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
