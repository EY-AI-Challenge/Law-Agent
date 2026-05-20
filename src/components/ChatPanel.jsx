import { useState, useRef, useEffect } from 'react'
import { Send, Bot } from 'lucide-react'
import { askAssistant } from '../services/api'

const QUICK_QUESTIONS = [
  'Conflitos entre CT e CC',
  'Cluster mais denso',
  'Leis mais influentes',
  'Inconsistências detetadas',
]

export default function ChatPanel({ pendingQuestion, onPendingHandled }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Olá! Sou o assistente legal da EY. Exploro as relações entre o **Código do Trabalho** e o **Código Civil** português.\n\nClica num nó do grafo para análise detalhada, ou faz-me uma pergunta.',
      highlight: 'Dica: clica num nó para enviar contexto automático para o chat.',
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (pendingQuestion) {
      handleSend(pendingQuestion.text, pendingQuestion.context)
      onPendingHandled()
    }
  }, [pendingQuestion])

  async function handleSend(text, context = null) {
    const q = text || input.trim()
    if (!q) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text: q }])
    setLoading(true)
    try {
      const answer = await askAssistant(q, context)
      setMessages(m => [...m, { role: 'assistant', text: answer }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', text: 'Erro ao contactar o assistente. Verifica a ligação ao backend.' }])
    }
    setLoading(false)
  }

  return (
    <div className="w-64 bg-ey-darker border-l border-ey-border flex flex-col flex-shrink-0">

      {/* Header */}
      <div className="px-4 py-3 border-b border-ey-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-ey-yellow" />
          <span className="text-[13px] font-medium text-white">AI assistant</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-ey-yellow text-ey-dark font-medium">
          demo
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2" style={{ maxHeight: 'calc(100vh - 200px)' }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`msg-anim text-[11px] leading-relaxed rounded-xl px-3 py-2 ${
              msg.role === 'user'
                ? 'bg-[#3A3500] border border-[#6B6200] text-ey-yellow self-end max-w-[90%]'
                : 'bg-ey-panel border border-ey-border text-[#D0CFD8] self-start max-w-[95%]'
            }`}
          >
            <span dangerouslySetInnerHTML={{ __html: formatText(msg.text) }} />
            {msg.highlight && (
              <div className="mt-2 bg-[#1E2A1E] border border-[#2A5A2A] rounded-md px-2 py-1.5 text-[10px] text-[#7EC87E]">
                {msg.highlight}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="bg-ey-panel border border-ey-border rounded-xl px-3 py-2 self-start">
            <div className="flex gap-1 items-center">
              {[0,1,2].map(i => (
                <div key={i} className="w-1.5 h-1.5 bg-ey-muted rounded-full pulse-dot"
                  style={{ animationDelay: `${i * 0.2}s` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick questions */}
      <div className="px-3 pb-2 flex flex-wrap gap-1.5">
        {QUICK_QUESTIONS.map(q => (
          <button
            key={q}
            onClick={() => handleSend(q)}
            className="text-[10px] px-2 py-1 rounded-full border border-ey-border text-ey-muted hover:border-ey-yellow hover:text-ey-yellow transition-all"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="px-3 pb-3 border-t border-ey-border pt-2">
        <div className="flex gap-2 items-center">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Pergunta sobre a rede legal..."
            className="flex-1 bg-ey-panel border border-ey-border rounded-lg px-3 py-1.5 text-[11px] text-white placeholder-[#555] outline-none focus:border-ey-yellow transition-colors"
          />
          <button
            onClick={() => handleSend()}
            className="bg-ey-yellow w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 hover:opacity-90 transition-opacity"
          >
            <Send className="w-3.5 h-3.5 text-ey-dark" />
          </button>
        </div>
      </div>
    </div>
  )
}

function formatText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#FFE600">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>')
}
