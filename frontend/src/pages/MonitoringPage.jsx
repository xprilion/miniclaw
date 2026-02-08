import { useEffect, useState } from 'preact/hooks'
import { api, showStatus } from '../lib/utils'
import MonitoringDashboard from '../components/MonitoringDashboard'

const MonitoringPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Monitoring</h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Track system performance, token usage, and events
        </p>
      </div>

      {/* Tab Navigation */}
      <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav class="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('dashboard')}
            class={`whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium ${
              activeTab === 'dashboard'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('events')}
            class={`whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium ${
              activeTab === 'events'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Raw Events
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'dashboard' ? (
        <MonitoringDashboard />
      ) : (
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Raw Events</h2>
            <button
              onClick={() => window.location.reload()}
              class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
            >
              Refresh
            </button>
          </div>
          <div id="events-container">
            {/* The existing events display logic would go here */}
            <p class="text-gray-500 dark:text-gray-400">
              Raw events view coming soon...
            </p>
          </div>
        </div>
      )}
    </main>
  )
}

export default MonitoringPage