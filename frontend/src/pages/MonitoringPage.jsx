import { useEffect, useState, useRef } from 'preact/hooks'
import { api, showStatus } from '../lib/utils'

const MonitoringPage = () => {
  const [runtime, setRuntime] = useState(null)
  const [usage, setUsage] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [eventsLimit, setEventsLimit] = useState(120)
  const [pollingEnabled, setPollingEnabled] = useState(true)
  const [latestEventId, setLatestEventId] = useState(0)
  const eventsFeedRef = useRef(null)

  const loadRuntime = async () => {
    const data = await api('/api/runtime')
    setRuntime(data.runtime)
    return data.runtime
  }

  const loadUsage = async () => {
    const data = await api('/api/usage')
    setUsage(data.usage || [])
    return data.usage || []
  }

  const loadEvents = async (sinceId = 0, limit = eventsLimit) => {
    const data = await api(`/api/events?since_id=${sinceId}&limit=${limit}`)
    if (sinceId === 0) {
      // Initial load - replace events
      setEvents(data.events || [])
    } else {
      // Polling - append new events
      if (data.events && data.events.length > 0) {
        setEvents(prev => [...data.events, ...prev])
      }
    }
    setLatestEventId(data.latest_id || 0)
    return data.events || []
  }

  const reloadAll = async () => {
    try {
      await Promise.all([
        loadRuntime(),
        loadUsage(),
        loadEvents()
      ])
    } catch (error) {
      showStatus(`Failed to load data: ${error.message}`, 'error')
      throw error
    }
  }

  const scrollToBottom = () => {
    if (eventsFeedRef.current) {
      eventsFeedRef.current.scrollTop = eventsFeedRef.current.scrollHeight
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        await reloadAll()
        showStatus('', '')
        scrollToBottom()
      } catch (error) {
        showStatus(`Initialization failed: ${error.message}`, 'error')
      } finally {
        setLoading(false)
      }
    }
    
    init()
  }, [])

  // Polling effect for events
  useEffect(() => {
    if (!pollingEnabled) return
    
    const interval = setInterval(async () => {
      try {
        await loadEvents(latestEventId, eventsLimit)
        scrollToBottom()
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 5000) // Poll every 5 seconds

    return () => clearInterval(interval)
  }, [pollingEnabled, latestEventId, eventsLimit])

  const handleRefreshRuntime = async () => {
    try {
      await loadRuntime()
      showStatus('Runtime refreshed.', 'success')
    } catch (error) {
      showStatus(`Refresh failed: ${error.message}`, 'error')
    }
  }

  const handleRefreshEvents = async () => {
    try {
      await loadEvents(0, eventsLimit)
      scrollToBottom()
      showStatus('Events refreshed.', 'success')
    } catch (error) {
      showStatus(`Refresh failed: ${error.message}`, 'error')
    }
  }

  const togglePolling = () => {
    setPollingEnabled(!pollingEnabled)
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const formatEventData = (data) => {
    if (!data) return ''
    if (typeof data === 'string') return data
    return JSON.stringify(data, null, 2)
  }

  if (loading) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="miniclaw-loading-placeholder">
            <span>Loading monitoring data...</span>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Runtime Snapshot Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Runtime Snapshot</h2>
              <button
                onClick={handleRefreshRuntime}
                class="mt-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600 sm:mt-0"
              >
                Refresh Runtime
              </button>
            </div>
            <pre class="mt-4 min-h-[8rem] max-h-60 overflow-auto rounded-md bg-gray-100 p-4 text-sm font-mono dark:bg-gray-900">
              {JSON.stringify(runtime, null, 2)}
            </pre>
            
            <h2 class="mt-8 text-base font-medium text-gray-900 dark:text-white">Token Usage By Model</h2>
            <div class="mt-4 overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Provider
                    </th>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Model
                    </th>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Requests
                    </th>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Prompt
                    </th>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Completion
                    </th>
                    <th class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Total
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                  {usage.map((item, index) => (
                    <tr key={index}>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {item.provider?.name || item.provider_id || 'N/A'}
                      </td>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {item.model || 'N/A'}
                      </td>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {item.requests || 0}
                      </td>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {item.prompt_tokens || 0}
                      </td>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {item.completion_tokens || 0}
                      </td>
                      <td class="px-3 py-2 text-sm text-gray-900 dark:text-white">
                        {(item.prompt_tokens || 0) + (item.completion_tokens || 0)}
                      </td>
                    </tr>
                  ))}
                  {usage.length === 0 && (
                    <tr>
                      <td colSpan="6" class="px-3 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                        No usage data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Event Stream Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Event Stream</h2>
            
            <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="eventsLimit" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Poll Limit
                </label>
                <input
                  id="eventsLimit"
                  type="number"
                  min="1"
                  max="500"
                  value={eventsLimit}
                  onInput={(e) => setEventsLimit(Number(e.target.value))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div class="flex items-end">
                <button
                  onClick={togglePolling}
                  class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                >
                  {pollingEnabled ? 'Pause Polling' : 'Resume Polling'}
                </button>
              </div>
            </div>
            
            <div 
              ref={eventsFeedRef}
              class="mt-4 h-96 min-h-96 overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900 font-mono text-xs"
            >
              {events.length === 0 ? (
                <div class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                  No events yet.
                </div>
              ) : (
                events.map(event => (
                  <div key={event.id} class="mb-2 p-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0">
                    <div class="flex justify-between">
                      <span class="font-medium text-primary-600 dark:text-primary-400">
                        {event.type}
                      </span>
                      <span class="text-gray-500 dark:text-gray-400">
                        {formatTimestamp(event.timestamp)}
                      </span>
                    </div>
                    <div class="mt-1 text-gray-700 dark:text-gray-300">
                      {event.message}
                    </div>
                    {event.data && (
                      <details class="mt-1">
                        <summary class="cursor-pointer text-gray-500 dark:text-gray-400">
                          Data
                        </summary>
                        <pre class="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-auto max-h-32">
                          {formatEventData(event.data)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))
              )}
            </div>
            <div class="mt-4 flex justify-between">
              <button
                onClick={handleRefreshEvents}
                class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
              >
                Refresh Events
              </button>
              <div id="statusLine" class="text-sm status-line"></div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default MonitoringPage