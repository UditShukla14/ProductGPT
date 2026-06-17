import { cn } from "@/lib/utils"

function Switch({
  className,
  checked,
  onCheckedChange,
  id,
  ...props
}: Omit<React.ComponentProps<"input">, "type" | "onChange"> & {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
}) {
  return (
    <label className="inline-flex cursor-pointer items-center">
      <input
        id={id}
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(event) => onCheckedChange?.(event.target.checked)}
        className={cn("peer sr-only", className)}
        {...props}
      />
      <span className="relative inline-flex h-5 w-9 shrink-0 rounded-full border border-transparent bg-input shadow-xs transition-colors peer-checked:bg-primary peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50 after:absolute after:top-0.5 after:left-0.5 after:size-4 after:rounded-full after:bg-background after:shadow-sm after:transition-transform peer-checked:after:translate-x-4" />
    </label>
  )
}

export { Switch }
