import { useEffect, useRef, useState } from "react"
import { Loader2, MessageCircle, SendHorizontal, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { streamChatMessage } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ChatHistoryMessage } from "@/types/api"

interface ProductFloatingChatProps {
  productId: string
  productTitle: string
}

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  error?: string | null
}

export function ProductFloatingChat({ productId, productTitle }: ProductFloatingChatProps) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Reset thread when the selected product changes.
  useEffect(() => {
    abortRef.current?.abort()
    setMessages([])
    setInput("")
    setIsStreaming(false)
    setOpen(false)
  }, [productId])

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, isStreaming, open])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  async function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return

    const history: ChatHistoryMessage[] = messages
      .filter((m) => m.content)
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }))

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
    }
    const assistantId = `a-${Date.now()}`
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setInput("")
    setIsStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamChatMessage(
        { message: text, history, productId },
        {
          onToken: (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + chunk } : m
              )
            )
          },
          onError: (message) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      error: message,
                      content: m.content || "Something went wrong while answering.",
                    }
                  : m
              )
            )
          },
        },
        controller.signal
      )
    } catch (error) {
      if ((error as Error).name === "AbortError") return
      const message = error instanceof Error ? error.message : "Chat request failed"
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, error: message, content: m.content || message }
            : m
        )
      )
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      {open && (
        <div
          className={cn(
            "pointer-events-auto flex w-[min(100vw-2rem,24rem)] flex-col overflow-hidden rounded-2xl border bg-background shadow-xl",
            "h-[min(70svh,32rem)]"
          )}
        >
          <div className="flex items-start justify-between gap-2 border-b bg-muted/40 px-3 py-2.5">
            <div className="min-w-0">
              <p className="text-sm font-semibold">Ask about this product</p>
              <p className="truncate text-xs text-muted-foreground" title={productTitle}>
                {productTitle}
              </p>
              <p className="mt-0.5 text-[10px] text-muted-foreground">
                Scoped to this product only · no pricing
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              <X className="size-4" />
            </Button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.length === 0 && (
              <div className="rounded-lg border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
                Ask about matchups, SKU, compatible parts, or customers-also-bought for this
                product.
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "ml-auto max-w-[90%] rounded-2xl bg-primary px-3 py-2 text-xs text-primary-foreground"
                    : "mr-auto max-w-[95%] space-y-1.5"
                }
              >
                {message.role === "assistant" && (
                  <p className="text-[10px] font-medium text-muted-foreground">Assistant</p>
                )}
                <div
                  className={
                    message.role === "assistant"
                      ? "rounded-2xl border bg-card px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap"
                      : "whitespace-pre-wrap"
                  }
                >
                  {message.content ||
                    (isStreaming && message.role === "assistant" ? "…" : "")}
                </div>
                {message.error && (
                  <p className="text-[11px] text-destructive">{message.error}</p>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <form
            className="flex items-end gap-2 border-t p-2.5"
            onSubmit={(event) => {
              event.preventDefault()
              void handleSend()
            }}
          >
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  void handleSend()
                }
              }}
              rows={2}
              placeholder="Ask about this product…"
              disabled={isStreaming}
              className="min-h-14 flex-1 resize-none rounded-lg border bg-background px-2.5 py-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-60"
            />
            <Button
              type="submit"
              size="sm"
              disabled={isStreaming || !input.trim()}
              className="shrink-0"
            >
              {isStreaming ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <SendHorizontal className="size-3.5" />
              )}
            </Button>
          </form>
        </div>
      )}

      <Button
        type="button"
        size="lg"
        className="pointer-events-auto gap-2 rounded-full shadow-lg"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-label={open ? "Close product chat" : "Open product chat"}
      >
        {open ? <X className="size-4" /> : <MessageCircle className="size-4" />}
        {open ? "Close" : "Ask AI"}
      </Button>
    </div>
  )
}
