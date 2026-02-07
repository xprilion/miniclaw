import { useEffect, useState } from 'preact/hooks'
import { api, showStatus } from '../lib/utils'

const SchedulerPage = () => {
  const [jobs, setJobs] = useState([])
  const [schedulerStatus, setSchedulerStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedJobId, setSelectedJobId] = useState('')
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    interval_seconds: 300,
    enabled: true,
    send_to_telegram_chat_id: '',
    prompt: ''
  })

  const loadJobs = async () => {
    const data = await api('/api/scheduler')
    setSchedulerStatus(data.scheduler)
    setJobs(data.scheduler.jobs || [])
    return data.scheduler.jobs || []
  }

  const reloadJobs = async () => {
    try {
      await loadJobs()
    } catch (error) {
      showStatus(`Failed to load jobs: ${error.message}`, 'error')
      throw error
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        await reloadJobs()
        showStatus('', '')
      } catch (error) {
        showStatus(`Initialization failed: ${error.message}`, 'error')
      } finally {
        setLoading(false)
      }
    }
    
    init()
  }, [])

  const selectJob = (jobId) => {
    const job = jobs.find(item => item.id === jobId)
    if (!job) return
    
    setSelectedJobId(job.id)
    setFormData({
      id: job.id,
      name: job.name || '',
      interval_seconds: job.interval_seconds || 300,
      enabled: job.enabled !== false, // default to true if undefined
      send_to_telegram_chat_id: job.send_to_telegram_chat_id || '',
      prompt: job.prompt || ''
    })
  }

  const clearEditor = () => {
    setSelectedJobId('')
    setFormData({
      id: '',
      name: '',
      interval_seconds: 300,
      enabled: true,
      send_to_telegram_chat_id: '',
      prompt: ''
    })
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSaveJob = async () => {
    try {
      if (!formData.id.trim()) {
        throw new Error('Job ID is required')
      }
      if (!formData.name.trim()) {
        throw new Error('Job Name is required')
      }
      if (formData.interval_seconds < 10) {
        throw new Error('Interval must be at least 10 seconds')
      }
      if (!formData.prompt.trim()) {
        throw new Error('Prompt is required')
      }

      const payload = {
        id: formData.id.trim(),
        name: formData.name.trim(),
        interval_seconds: formData.interval_seconds,
        enabled: formData.enabled,
        send_to_telegram_chat_id: formData.send_to_telegram_chat_id.trim(),
        prompt: formData.prompt.trim()
      }

      await api('/api/scheduler/upsert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      await reloadJobs()
      setSelectedJobId(formData.id.trim())
      selectJob(formData.id.trim())
      showStatus('Job saved.', 'success')
    } catch (error) {
      showStatus(`Save job failed: ${error.message}`, 'error')
    }
  }

  const handleDeleteJob = async () => {
    try {
      if (!formData.id.trim()) {
        throw new Error('Job ID is required')
      }

      await api('/api/scheduler/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: formData.id.trim() })
      })

      await reloadJobs()
      clearEditor()
      showStatus('Job deleted.', 'success')
    } catch (error) {
      showStatus(`Delete job failed: ${error.message}`, 'error')
    }
  }

  const handleRunJobNow = async () => {
    try {
      if (!formData.id.trim()) {
        throw new Error('Job ID is required')
      }

      const result = await api('/api/scheduler/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: formData.id.trim() })
      })

      showStatus(`Job triggered: ${result.result.message || 'Success'}`, 'success')
    } catch (error) {
      showStatus(`Run job failed: ${error.message}`, 'error')
    }
  }

  const handleRefresh = async () => {
    try {
      await reloadJobs()
      showStatus('Jobs refreshed.', 'success')
    } catch (error) {
      showStatus(`Refresh failed: ${error.message}`, 'error')
    }
  }

  const formatNextRun = (job) => {
    if (!job.next_run_at) return 'Not scheduled'
    const nextRun = new Date(job.next_run_at)
    return nextRun.toLocaleString()
  }

  if (loading) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="miniclaw-loading-placeholder">
            <span>Loading jobs...</span>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Jobs Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Jobs</h2>
              <div class="mt-3 flex space-x-2 sm:mt-0">
                <button
                  onClick={clearEditor}
                  class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                >
                  New
                </button>
                <button
                  onClick={handleRefresh}
                  class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                >
                  Refresh
                </button>
              </div>
            </div>
            <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Status: {schedulerStatus?.enabled ? 'Enabled' : 'Disabled'} | 
              Active: {schedulerStatus?.active_jobs || 0} | 
              Next wake: {schedulerStatus?.next_wake_at ? new Date(schedulerStatus.next_wake_at).toLocaleTimeString() : 'N/A'}
            </div>
            <div
              id="jobsList"
              class="mt-4 h-96 min-h-96 overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900"
            >
              {jobs.length === 0 ? (
                <div class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                  No jobs yet.
                </div>
              ) : (
                jobs.map(job => {
                  const isSelected = selectedJobId === job.id
                  
                  return (
                    <div
                      key={job.id}
                      class={`feed-item ${isSelected ? 'selected' : ''} cursor-pointer`}
                      onClick={() => selectJob(job.id)}
                    >
                      <div class="feed-meta">
                        {job.id} {job.enabled !== false ? (
                          <span class="badge badge-success text-xs">Enabled</span>
                        ) : (
                          <span class="badge badge-warning text-xs">Disabled</span>
                        )}
                      </div>
                      <div class="feed-body">
                        {job.name}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Interval: {job.interval_seconds}s | Next: {formatNextRun(job)}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>

        {/* Job Editor Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Job Editor</h2>
            
            <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="jobIdInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Job ID
                </label>
                <input
                  id="jobIdInput"
                  value={formData.id}
                  onInput={(e) => handleInputChange('id', e.target.value)}
                  placeholder="daily_report"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div>
                <label htmlFor="jobNameInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Job Name
                </label>
                <input
                  id="jobNameInput"
                  value={formData.name}
                  onInput={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Daily Report"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>

            <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="jobIntervalInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Interval (seconds)
                </label>
                <input
                  id="jobIntervalInput"
                  type="number"
                  min="10"
                  value={formData.interval_seconds}
                  onInput={(e) => handleInputChange('interval_seconds', Number(e.target.value))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div class="flex items-end">
                <div class="flex items-center">
                  <input
                    id="jobEnabledInput"
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) => handleInputChange('enabled', e.target.checked)}
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:ring-offset-gray-800"
                  />
                  <label htmlFor="jobEnabledInput" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                    Enabled
                  </label>
                </div>
              </div>
            </div>

            <div class="mt-4">
              <label htmlFor="jobTelegramChatInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Send output to Telegram chat ID (optional)
              </label>
              <input
                id="jobTelegramChatInput"
                value={formData.send_to_telegram_chat_id}
                onInput={(e) => handleInputChange('send_to_telegram_chat_id', e.target.value)}
                placeholder="123456789"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div class="mt-4">
              <label htmlFor="jobPromptInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Prompt
              </label>
              <textarea
                id="jobPromptInput"
                rows="4"
                value={formData.prompt}
                onInput={(e) => handleInputChange('prompt', e.target.value)}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Summarize overnight alerts and propose top 3 actions."
              ></textarea>
            </div>

            <div class="mt-6 flex flex-wrap gap-2">
              <button
                onClick={handleSaveJob}
                class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Save Job
              </button>
              <button
                onClick={handleDeleteJob}
                class="inline-flex items-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Delete Job
              </button>
              <button
                onClick={handleRunJobNow}
                class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
              >
                Run Now
              </button>
            </div>
            <div id="statusLine" class="mt-4 text-sm status-line"></div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default SchedulerPage