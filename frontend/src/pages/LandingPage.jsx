import { useEffect, useState } from 'preact/hooks'
import { api } from '../lib/utils'

const LandingPage = () => {
  const [health, setHealth] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [healthData, configData] = await Promise.all([
          api('/api/health'),
          api('/api/config')
        ])
        setHealth(healthData)
        setConfig(configData.config)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="miniclaw-loading-placeholder">
            <span>Loading...</span>
          </div>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="text-red-500 dark:text-red-400">
            Error: {error}
          </div>
        </div>
      </main>
    )
  }

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="text-center mb-12">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
          Welcome to MiniClaw
        </h1>
        <p class="mt-3 text-xl text-gray-500 dark:text-gray-400">
          Your lightweight personal AI assistant
        </p>
      </div>

      <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Health Status */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">System Status</h2>
            <div class="mt-4">
              <div class="flex items-center">
                <div class="status-indicator online"></div>
                <span class="text-sm font-medium text-green-600 dark:text-green-400">
                  System Online
                </span>
              </div>
              <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Last checked: {new Date(health.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Configuration Summary */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Configuration</h2>
            <div class="mt-4 space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-500 dark:text-gray-400">Agent Name:</span>
                <span class="font-medium text-gray-900 dark:text-white">{config?.agent?.name || 'N/A'}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-500 dark:text-gray-400">Active Channel:</span>
                <span class="font-medium text-gray-900 dark:text-white">
                  {config?.channels?.active_channel || 'N/A'}
                </span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-500 dark:text-gray-400">Memory Enabled:</span>
                <span class="font-medium text-gray-900 dark:text-white">
                  {config?.memory?.enabled ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Quick Actions</h2>
            <div class="mt-4 space-y-3">
              <a 
                href="/chat" 
                class="block w-full rounded-md bg-primary-600 px-4 py-2 text-center text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Start Chatting
              </a>
              <a 
                href="/setup" 
                class="block w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-center text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
              >
                Configure Settings
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Features Overview */}
      <div class="mt-12">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Features</h2>
        <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Chat Interface</h3>
              <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Interactive chat with your AI assistant, supporting multiple models and providers.
              </p>
              <div class="mt-4">
                <a 
                  href="/chat" 
                  class="text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  Go to Chat
                </a>
              </div>
            </div>
          </div>

          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Skills Management</h3>
              <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Create and manage custom skills to extend your assistant's capabilities.
              </p>
              <div class="mt-4">
                <a 
                  href="/skills" 
                  class="text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  Manage Skills
                </a>
              </div>
            </div>
          </div>

          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Task Scheduler</h3>
              <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Schedule automated tasks and receive periodic reports and updates.
              </p>
              <div class="mt-4">
                <a 
                  href="/scheduler" 
                  class="text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  Schedule Tasks
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default LandingPage