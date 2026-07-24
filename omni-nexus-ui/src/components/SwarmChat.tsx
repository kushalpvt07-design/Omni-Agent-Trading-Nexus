"use client"

import { useState, useRef, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send } from "lucide-react"
import { LogMessage } from "@/hooks/useSwarmWebSocket"

// FACT: Pass the active hook state as props so you don't fork the connection.
interface SwarmChatProps {
  deployDirective: (directive: string) => void;
  isConnected: boolean;
  externalLogs: LogMessage[];
}

export function SwarmChat({ deployDirective, isConnected, externalLogs }: SwarmChatProps) {
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [externalLogs])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !isConnected) return
    
    deployDirective(input)
    setInput("")
  }

  // Filter logs to only show relevant chat messages (ignoring pure state updates)
  const chatLogs = externalLogs.filter(log => 
    log.type !== undefined && ["message", "status", "checkpoint", "user"].includes(log.type)
  )

  return (
    <div className="flex flex-col h-[400px] border border-slate-800 rounded-lg bg-slate-950 p-4 mt-8">
      <h3 className="text-lg font-semibold text-slate-100 mb-2">Swarm Command Terminal</h3>
      <ScrollArea className="flex-1 mb-4 pr-4">
        {chatLogs.length === 0 ? (
           <div className="text-sm text-slate-500 italic">System standby...</div>
        ) : (
          chatLogs.map((msg, idx) => (
            <div key={idx} className={`mb-2 text-sm ${msg.role === 'USER' ? 'text-slate-300' : msg.role === 'SYSTEM' ? 'text-emerald-500' : 'text-blue-400'}`}>
              <span className="font-bold">{msg.role}: </span>
              {msg.content}
            </div>
          ))
        )}
        <div ref={scrollRef} />
      </ScrollArea>
      
      <form onSubmit={handleSend} className="flex gap-2">
        <Input 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isConnected ? "Execute trading directive..." : "Nexus offline..."} 
          className="bg-slate-900 border-slate-800 text-slate-100"
          disabled={!isConnected}
        />
        <Button type="submit" size="icon" variant="secondary" disabled={!isConnected || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
