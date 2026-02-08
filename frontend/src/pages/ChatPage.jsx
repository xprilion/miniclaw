import { useEffect, useState, useRef } from 'preact/hooks'
import { api, streamApi, showStatus } from '../lib/utils'

const ChatPage = () => {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState(null)
  const messagesEndRef = useRef(null)
  const hasReceivedFinalResultRef = useRef(false)

  const loadConfig = async () => {
    const data = await api('/api/config')
    setConfig(data.config)
    return data.config
  }

  useEffect(() => {
    const init = async () => {
      try {
        await loadConfig()
        showStatus('', '')
      } catch (error) {
        showStatus(`Initialization failed: ${error.message}`, 'error')
      }
    }
    
    init()
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return

    try {
      setLoading(true)
      
      // Add user message to chat
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: inputMessage,
        timestamp: new Date().toISOString()
      }
      
      setMessages(prev => [...prev, userMessage])
      setInputMessage('')
      
      // Create assistant message placeholder
      const assistantMessageId = Date.now() + 1
      const assistantMessagePlaceholder = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString()
      }
      
      setMessages(prev => [...prev, assistantMessagePlaceholder])
      
      // Stream response from API – use ref so callback never applies result/error twice
      hasReceivedFinalResultRef.current = false

      const contentFromData = (data) => {
        if (data == null) return ''
        if (typeof data === 'string') return data
        return data.response ?? data.message ?? data.raw ?? (typeof data.error === 'string' ? `Error: ${data.error}` : '')
      }

      await streamApi('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: inputMessage,
          source: 'web',
          stream: true
        })
      }, (eventType, data) => {
        if (eventType === 'result') {
          if (hasReceivedFinalResultRef.current) return
          hasReceivedFinalResultRef.current = true
          const responseContent = contentFromData(data) || 'No response'
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: responseContent }
              : msg
          ))
          setLoading(false)
          return
        }
        if (eventType === 'error') {
          if (hasReceivedFinalResultRef.current) return
          hasReceivedFinalResultRef.current = true
          const errMsg = typeof data?.error === 'string' ? data.error : 'Unknown error'
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, role: 'error', content: `Error: ${errMsg}` }
              : msg
          ))
          setLoading(false)
          return
        }
        if (eventType === 'status' || eventType === 'thinking') {
          if (hasReceivedFinalResultRef.current) return
          const text = contentFromData(data)
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: text }
              : msg
          ))
        }
      })
    } catch (error) {
      showStatus(`Failed to send message: ${error.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="flex flex-col h-[calc(100vh-12rem)]">
        <div class="flex items-center justify-between mb-4">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Chat</h1>
          <button
            onClick={clearChat}
            class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
          >
            Clear Chat
          </button>
        </div>
        
        <div class="flex-1 overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800 flex flex-col">
          <div class="flex-1 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div class="flex h-full items-center justify-center">
                <div class="text-center">
                  <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No messages</h3>
                  <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Start a conversation with your AI assistant.
                  </p>
                </div>
              </div>
            ) : (
              <div class="space-y-4">
                {messages.map((message) => (
                  <div 
                    key={message.id} 
                    class={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div 
                      class={`max-w-[80%] rounded-lg px-4 py-2 ${
                        message.role === 'user' 
                          ? 'bg-primary-600 text-white' 
                          : message.role === 'error'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                      }`}
                    >
                      <div class="whitespace-pre-wrap">
                        {typeof message.content === 'string' ? message.content : (message.content?.response ?? message.content?.raw ?? String(message.content ?? ''))}
                      </div>
                      <div 
                        class={`text-xs mt-1 ${
                          message.role === 'user' 
                            ? 'text-primary-100' 
                            : message.role === 'error'
                              ? 'text-red-600 dark:text-red-300'
                              : 'text-gray-500 dark:text-gray-400'
                        }`}
                      >
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div class="flex justify-start">
                    <div class="rounded-lg bg-gray-100 px-4 py-2 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                      <div class="flex items-center">
                        <div class="h-2 w-2 animate-pulse rounded-full bg-gray-400 mr-2"></div>
                        <div class="h-2 w-2 animate-pulse rounded-full bg-gray-400 mr-2 delay-75"></div>
                        <div class="h-2 w-2 animate-pulse rounded-full bg-gray-400"></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
          
          <div class="border-t border-gray-200 dark:border-gray-700 p-4">
            <div class="flex">
              <textarea
                value={inputMessage}
                onInput={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type your message..."
                disabled={loading}
                rows="2"
                class="flex-1 rounded-l-md border border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              ></textarea>
              <button
                onClick={handleSendMessage}
                disabled={loading || !inputMessage.trim()}
                class="rounded-r-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
            <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Press Enter to send, Shift+Enter for new line
            </div>
          </div>
        </div>
        
        <div id="statusLine" class="mt-4 text-sm status-line"></div>
      </div>
    </main>
  )
}

export default ChatPage