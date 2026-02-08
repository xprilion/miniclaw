import { useEffect, useState } from 'preact/hooks'
import { api } from '../lib/utils'

const MonitoringDashboard = () => {
  const [events, setEvents] = useState([])
  const [usage, setUsage] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('1h')

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [eventsData, usageData] = await Promise.all([
          api(`/api/events?limit=100`),
          api(`/api/usage?limit=50`)
        ])
        
        setEvents(eventsData.events || [])
        setUsage(usageData.usage || [])
      } catch (error) {
        console.error('Failed to fetch monitoring data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const getEventTypeClass = (eventType) => {
    if (eventType.includes('error')) return 'text-red-600 dark:text-red-400'
    if (eventType.includes('success')) return 'text-green-600 dark:text-green-400'
    if (eventType.includes('warning')) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatDuration = (seconds) => {
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
    return `${seconds.toFixed(2)}s`
  }

  const getTotalTokens = () => {
    return usage.reduce((total, item) => total + (item.total_tokens || 0), 0)
  }

  const getCostEstimate = () => {
    // Rough cost estimate based on token usage (simplified)
    const totalTokens = getTotalTokens()
    const costPerMillion = 0.01 // Example cost
    return (totalTokens / 1000000 * costPerMillion).toFixed(4)
  }

  if (loading && events.length === 0) {
    return (
      <div class="flex justify-center items-center h-64">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div class="space-y-6">
      {/* Summary Cards */}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="rounded-full bg-blue-100 dark:bg-blue-900 p-3">
              <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
            <div class="ml-4">
              <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Tokens</h3>
              <p class="text-2xl font-semibold text-gray-900 dark:text-white">{getTotalTokens().toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="rounded-full bg-green-100 dark:bg-green-900 p-3">
              <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <div class="ml-4">
              <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Estimated Cost</h3>
              <p class="text-2xl font-semibold text-gray-900 dark:text-white">${getCostEstimate()}</p>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="rounded-full bg-purple-100 dark:bg-purple-900 p-3">
              <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            <div class="ml-4">
              <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Recent Events</h3>
              <p class="text-2xl font-semibold text-gray-900 dark:text-white">{events.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Time Range Selector */}
      <div class="flex justify-end">
        <div class="inline-flex rounded-md shadow-sm">
          {['1h', '6h', '12h', '24h', '7d'].map((range) => (
            <button
              key={range}
              type="button"
              class={`px-4 py-2 text-sm font-medium ${
                timeRange === range
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
              } border border-gray-300 dark:border-gray-600 ${
                range === '1h' ? 'rounded-l-lg' : ''
              } ${range === '7d' ? 'rounded-r-md' : ''} ${
                range !== '1h' && range !== '7d' ? '-ml-px' : ''
              }`}
              onClick={() => setTimeRange(range)}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Events Timeline */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Events</h3>
        </div>
        <div class="p-6">
          <div class="flow-root">
            <ul class="space-y-4">
              {events.slice(0, 20).map((event) => (
                <li key={event.id} class="relative pl-8">
                  <div class="absolute left-0 top-1 w-4 h-4 rounded-full bg-primary-500"></div>
                  <div class="flex justify-between">
                    <div>
                      <p class={`text-sm font-medium ${getEventTypeClass(event.type)}`}>
                        {event.type}
                      </p>
                      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {event.description}
                      </p>
                      {event.data && Object.keys(event.data).length > 0 && (
                        <details class="mt-2">
                          <summary class="text-xs text-gray-400 cursor-pointer">Details</summary>
                          <pre class="mt-2 text-xs bg-gray-50 dark:bg-gray-700 p-2 rounded overflow-x-auto">
                            {JSON.stringify(event.data, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                    <div class="text-right">
                      <p class="text-sm text-gray-500 dark:text-gray-400">
                        {formatTimestamp(event.timestamp)}
                      </p>
                      {event.data?.duration_seconds && (
                        <p class="text-xs text-gray-400 dark:text-gray-500">
                          {formatDuration(event.data.duration_seconds)}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Usage Chart */}
      {usage.length > 0 && (
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">Token Usage</h3>
          </div>
          <div class="p-6">
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead class="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Provider</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Model</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Prompt Tokens</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Completion Tokens</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Total Tokens</th>
                  </tr>
                </thead>
                <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {usage.map((item, index) => (
                    <tr key={index} class={index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700'}>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {item.provider_id}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {item.model}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {item.prompt_tokens?.toLocaleString() || '0'}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {item.completion_tokens?.toLocaleString() || '0'}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {item.total_tokens?.toLocaleString() || '0'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MonitoringDashboard