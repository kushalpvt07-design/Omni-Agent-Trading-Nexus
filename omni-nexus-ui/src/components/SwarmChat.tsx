"use client"

import { useState, useEffect, useRef } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send } from "lucide-react"

export function SwarmChat() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<{role: string, content: string}[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Establish WebSocket connection to FastAPI backend
    const ws = new WebSocket("ws://127.0.0.1:8000/api/v1/swarm-stream")
    
    ws.onopen = () => {
      setIsConnected(true)
      setMessages(prev => [...prev, { role: "System", content: "WebSocket Connected: Standing by for directives." }])
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === "message") {
          setMessages(prev => [...prev, { role: data.role || "Swarm", content: data.content }])
        }
      } catch (err) {
        setMessages(prev => [...prev, { role: "Swarm", content: event.data }])
      }
    }
    
    ws.onclose = () => {
      setIsConnected(false)
      setMessages(prev => [...prev, { role: "System", content: "WebSocket Disconnected." }])
    }
    
    ws.onerror = (error) => {
      console.error("WebSocket Error:", error)
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // Add user message locally for instant feedback
    setMessages(prev => [...prev, { role: "User", content: input }])
    
    // Push `input` down the WebSocket connection to the FastAPI backend
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({ directive: input, paper_trading: true }))
    } else {
      setMessages(prev => [...prev, { role: "System", content: "Error: Not connected to swarm." }])
    }
    
    setInput("")
  }

  return (
    <div className="flex flex-col h-[400px] border border-slate-800 rounded-lg bg-slate-950 p-4 mt-8">
      <h3 className="text-lg font-semibold text-slate-100 mb-2">Swarm Command Terminal</h3>
      <ScrollArea className="flex-1 mb-4 pr-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`mb-2 text-sm ${msg.role === 'User' ? 'text-slate-300' : msg.role === 'System' ? 'text-emerald-500' : 'text-blue-400'}`}>
            <span className="font-bold">{msg.role}: </span>
            {msg.content}
          </div>
        ))}
      </ScrollArea>
      
      <form onSubmit={handleSend} className="flex gap-2">
        <Input 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Execute trading directive..." 
          className="bg-slate-900 border-slate-800 text-slate-100"
          disabled={!isConnected}
        />
        <Button type="submit" size="icon" variant="secondary" disabled={!isConnected}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
