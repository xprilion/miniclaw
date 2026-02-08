import { useEffect, useState, useContext } from 'preact/hooks'
import { AppContext } from '../main'
import { api, showStatus } from '../lib/utils'

const SimplifiedSetupPage = () => {
  const { theme } = useContext(AppContext)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeSection, setActiveSection] = useState('providers')
  const [testResults, setTestResults] = useState({})

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true)
        const data = await api('/api/config')
        setConfig(data.config)
        showStatus('', '')
      } catch (error) {
        showStatus(`Failed to load config: ${error.message}`, 'error')
      } finally {
        setLoading(false)
      }
    }

    loadConfig()
  }, [])

  const handleSaveConfig = async () => {
    try {
      setSaving(true)
      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      showStatus('Configuration saved successfully!', 'success')
    } catch (error) {
      showStatus(`Failed to save config: ${error.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const updateConfig = (path, value) => {
    const newConfig = { ...config }
    let current = newConfig
    const parts = path.split('.')
    const lastPart = parts.pop()

    for (const part of parts) {
      if (!(part in current)) {
        current[part] = {}
      }
      current = current[part]
    }

    current[lastPart] = value
    setConfig(newConfig)
  }

  const addProvider = () => {
    const newProvider = {
      id: `provider_${Date.now()}`,
      name: 'New Provider',
      type: 'ollama',
      enabled: true,
      base_url: 'http://localhost:11434',
      api_key: '',
      model: 'qwen3',
      temperature: 0.2,
      timeout_seconds: 300,
      verify_tls: true,
      system_prompt_override: ''
    }

    const newConfig = { ...config }
    newConfig.providers.items.push(newProvider)
    setConfig(newConfig)
  }

  const removeProvider = (index) => {
    const newConfig = { ...config }
    newConfig.providers.items.splice(index, 1)
    setConfig(newConfig)
  }

  const setDefaultProvider = (index) => {
    const newConfig = { ...config }
    newConfig.providers.default_provider_id = newConfig.providers.items[index].id
    setConfig(newConfig)
  }

  const testProvider = async (index) => {
    try {
      const provider = config.providers.items[index]
      setTestResults(prev => ({ ...prev, [provider.id]: { loading: true } }))
      
      const models = await api(`/api/models?provider_id=${provider.id}`)
      setTestResults(prev => ({ 
        ...prev, 
        [provider.id]: { 
          loading: false, 
          success: true, 
          message: `Found ${models.models.length} models`,
          models: models.models
        } 
      }))
    } catch (error) {
      setTestResults(prev => ({ 
        ...prev, 
        [provider.id]: { 
          loading: false, 
          success: false, 
          message: error.message 
        } 
      }))
    }
  }

  const testTelegram = async () => {
    try {
      setTestResults(prev => ({ ...prev, telegram: { loading: true } }))
      
      // Test with bound chat ID if available, otherwise show message
      const telegramCfg = config.telegram || {}
      const allowedChatIds = telegramCfg.allowed_chat_ids || []
      const boundChatId = allowedChatIds.length > 0 ? allowedChatIds[0] : null
      
      if (boundChatId) {
        await api('/api/telegram/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: 'MiniClaw test message'
            // chat_id will be automatically used from bound chat
          })
        })
        setTestResults(prev => ({ 
          ...prev, 
          telegram: { 
            loading: false, 
            success: true, 
            message: `Test message sent to chat ${boundChatId}` 
          } 
        }))
      } else {
        setTestResults(prev => ({ 
          ...prev, 
          telegram: { 
            loading: false, 
            success: true, 
            message: 'Telegram configured but no chat bound yet. Pair a chat first.' 
          } 
        }))
      }
    } catch (error) {
      setTestResults(prev => ({ 
        ...prev, 
        telegram: { 
          loading: false, 
          success: false, 
          message: error.message 
        } 
      }))
    }
  }

  const testWhatsApp = async () => {
    try {
      setTestResults(prev => ({ ...prev, whatsapp: { loading: true } }))
      
      // For now, just show configuration status
      const whatsappCfg = config.channels?.whatsapp_wacli || {}
      if (whatsappCfg.enabled) {
        setTestResults(prev => ({ 
          ...prev, 
          whatsapp: { 
            loading: false, 
            success: true, 
            message: 'WhatsApp integration enabled. Make sure wacli is properly configured.' 
          } 
        }))
      } else {
        setTestResults(prev => ({ 
          ...prev, 
          whatsapp: { 
            loading: false, 
            success: true, 
            message: 'WhatsApp integration disabled.' 
          } 
        }))
      }
    } catch (error) {
      setTestResults(prev => ({ 
        ...prev, 
        whatsapp: { 
          loading: false, 
          success: false, 
          message: error.message 
        } 
      }))
    }
  }

  const getBoundChatId = () => {
    const telegramCfg = config.telegram || {}
    const allowedChatIds = telegramCfg.allowed_chat_ids || []
    return allowedChatIds.length > 0 ? allowedChatIds[0] : null
  }

  if (loading) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="miniclaw-loading-placeholder">
            <span>Loading configuration...</span>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Simplified Setup</h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure your MiniClaw instance with essential settings
        </p>
      </div>

      {/* Section Navigation */}
      <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav class="-mb-px flex space-x-8">
          {[
            { id: 'providers', name: 'AI Providers' },
            { id: 'channels', name: 'Communication' },
            { id: 'tools', name: 'Tools & Security' },
            { id: 'memory', name: 'Memory' }
          ].map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              class={`whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium ${
                activeSection === section.id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {section.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Configuration Sections */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <div class="flex justify-between items-center">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">
              {activeSection === 'providers' && 'AI Model Providers'}
              {activeSection === 'channels' && 'Communication Channels'}
              {activeSection === 'tools' && 'Tools & Security'}
              {activeSection === 'memory' && 'Memory Configuration'}
            </h2>
            <button
              onClick={handleSaveConfig}
              disabled={saving}
              class="rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        <div class="p-6">
          {/* AI Providers Section */}
          {activeSection === 'providers' && (
            <div class="space-y-6">
              <div class="flex justify-between items-center">
                <h3 class="text-md font-medium text-gray-900 dark:text-white">Model Providers</h3>
                <button
                  onClick={addProvider}
                  class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                >
                  Add Provider
                </button>
              </div>

              <div class="space-y-4">
                {config.providers.items.map((provider, index) => (
                  <div key={provider.id} class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div class="flex justify-between items-start mb-3">
                      <div class="flex items-center">
                        <input
                          type="radio"
                          name="defaultProvider"
                          checked={config.providers.default_provider_id === provider.id}
                          onChange={() => setDefaultProvider(index)}
                          class="h-4 w-4 text-primary-600 focus:ring-primary-500"
                        />
                        <span class="ml-2 text-sm font-medium text-gray-900 dark:text-white">
                          {provider.name}
                        </span>
                        {config.providers.default_provider_id === provider.id && (
                          <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200">
                            Default
                          </span>
                        )}
                      </div>
                      <div class="flex space-x-2">
                        <button
                          onClick={() => testProvider(index)}
                          class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300"
                        >
                          Test
                        </button>
                        <button
                          onClick={() => removeProvider(index)}
                          class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                        >
                          Remove
                        </button>
                      </div>
                    </div>

                    {/* Test Results */}
                    {testResults[provider.id] && (
                      <div class={`mb-3 p-2 rounded text-sm ${
                        testResults[provider.id].success 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' 
                          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
                      }`}>
                        {testResults[provider.id].loading ? (
                          'Testing...'
                        ) : (
                          <>
                            {testResults[provider.id].message}
                            {testResults[provider.id].models && (
                              <details class="mt-1">
                                <summary class="cursor-pointer">Available Models</summary>
                                <ul class="mt-1 list-disc list-inside">
                                  {testResults[provider.id].models.slice(0, 5).map(model => (
                                    <li key={model.name}>{model.name}</li>
                                  ))}
                                  {testResults[provider.id].models.length > 5 && (
                                    <li>+ {testResults[provider.id].models.length - 5} more</li>
                                  )}
                                </ul>
                              </details>
                            )}
                          </>
                        )}
                      </div>
                    )}

                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Name
                        </label>
                        <input
                          type="text"
                          value={provider.name}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].name = e.target.value
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Type
                        </label>
                        <select
                          value={provider.type}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].type = e.target.value
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        >
                          <option value="ollama">Ollama</option>
                          <option value="openai_compatible">OpenAI Compatible</option>
                          <option value="litellm">LiteLLM</option>
                          <option value="openrouter">OpenRouter</option>
                        </select>
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Base URL
                        </label>
                        <input
                          type="text"
                          value={provider.base_url}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].base_url = e.target.value
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Model
                        </label>
                        <input
                          type="text"
                          value={provider.model}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].model = e.target.value
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          API Key
                        </label>
                        <input
                          type="password"
                          value={provider.api_key}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].api_key = e.target.value
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Temperature
                        </label>
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.1"
                          value={provider.temperature}
                          onInput={(e) => {
                            const newConfig = { ...config }
                            newConfig.providers.items[index].temperature = parseFloat(e.target.value)
                            setConfig(newConfig)
                          }}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                    </div>

                    <div class="mt-4 flex items-center">
                      <input
                        type="checkbox"
                        checked={provider.enabled}
                        onInput={(e) => {
                          const newConfig = { ...config }
                          newConfig.providers.items[index].enabled = e.target.checked
                          setConfig(newConfig)
                        }}
                        class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label class="ml-2 block text-sm text-gray-900 dark:text-white">
                        Enabled
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Communication Channels Section */}
          {activeSection === 'channels' && (
            <div class="space-y-6">
              {/* Telegram Section */}
              <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.telegram.enabled}
                      onInput={(e) => updateConfig('telegram.enabled', e.target.checked)}
                      class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <label class="ml-2 block text-sm font-medium text-gray-900 dark:text-white">
                      Enable Telegram Integration
                    </label>
                  </div>
                  <button
                    onClick={testTelegram}
                    class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                  >
                    Test
                  </button>
                </div>

                {testResults.telegram && (
                  <div class={`mt-3 p-2 rounded text-sm ${
                    testResults.telegram.success 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' 
                      : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
                  }`}>
                    {testResults.telegram.loading ? 'Testing...' : testResults.telegram.message}
                  </div>
                )}

                {config.telegram.enabled && (
                  <div class="mt-4 space-y-4">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Bot Token
                      </label>
                      <input
                        type="password"
                        value={config.telegram.bot_token}
                        onInput={(e) => updateConfig('telegram.bot_token', e.target.value)}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        placeholder="Enter your Telegram bot token"
                      />
                      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Create a bot with <a href="https://t.me/BotFather" target="_blank" class="text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300">@BotFather</a>
                      </p>
                    </div>

                    <div class="flex items-center">
                      <input
                        type="checkbox"
                        checked={config.telegram.pairing_required}
                        onInput={(e) => updateConfig('telegram.pairing_required', e.target.checked)}
                        class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label class="ml-2 block text-sm text-gray-900 dark:text-white">
                        Require Pairing for Security
                      </label>
                    </div>

                    {getBoundChatId() && (
                      <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                        <p class="text-sm text-blue-800 dark:text-blue-200">
                          <span class="font-medium">Bound Chat ID:</span> {getBoundChatId()}
                        </p>
                        <p class="text-xs text-blue-600 dark:text-blue-300 mt-1">
                          To change the bound chat, unbind the current one or pair a new chat via Telegram.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* WhatsApp Section */}
              <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.channels?.whatsapp_wacli?.enabled || false}
                      onInput={(e) => {
                        const newConfig = { ...config }
                        if (!newConfig.channels) newConfig.channels = {}
                        if (!newConfig.channels.whatsapp_wacli) newConfig.channels.whatsapp_wacli = {}
                        newConfig.channels.whatsapp_wacli.enabled = e.target.checked
                        setConfig(newConfig)
                      }}
                      class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <label class="ml-2 block text-sm font-medium text-gray-900 dark:text-white">
                      Enable WhatsApp Integration (wacli)
                    </label>
                  </div>
                  <button
                    onClick={testWhatsApp}
                    class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                  >
                    Check
                  </button>
                </div>

                {testResults.whatsapp && (
                  <div class={`mt-3 p-2 rounded text-sm ${
                    testResults.whatsapp.success 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' 
                      : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
                  }`}>
                    {testResults.whatsapp.loading ? 'Checking...' : testResults.whatsapp.message}
                  </div>
                )}

                {config.channels?.whatsapp_wacli?.enabled && (
                  <div class="mt-4 space-y-4">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        wacli Command
                      </label>
                      <input
                        type="text"
                        value={config.channels?.whatsapp_wacli?.wacli_command || 'wacli'}
                        onInput={(e) => {
                          const newConfig = { ...config }
                          if (!newConfig.channels) newConfig.channels = {}
                          if (!newConfig.channels.whatsapp_wacli) newConfig.channels.whatsapp_wacli = {}
                          newConfig.channels.whatsapp_wacli.wacli_command = e.target.value
                          setConfig(newConfig)
                        }}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        placeholder="wacli"
                      />
                    </div>

                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Session Name
                      </label>
                      <input
                        type="text"
                        value={config.channels?.whatsapp_wacli?.session || ''}
                        onInput={(e) => {
                          const newConfig = { ...config }
                          if (!newConfig.channels) newConfig.channels = {}
                          if (!newConfig.channels.whatsapp_wacli) newConfig.channels.whatsapp_wacli = {}
                          newConfig.channels.whatsapp_wacli.session = e.target.value
                          setConfig(newConfig)
                        }}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        placeholder="default"
                      />
                      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Make sure wacli is properly installed and configured. See <a href="https://github.com/steipete/wacli" target="_blank" class="text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300">wacli documentation</a>.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tools & Security Section */}
          {activeSection === 'tools' && (
            <div class="space-y-6">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.tools.enabled}
                    onInput={(e) => updateConfig('tools.enabled', e.target.checked)}
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm font-medium text-gray-900 dark:text-white">
                    Enable Tools
                  </label>
                </div>
                <span class="text-sm text-gray-500 dark:text-gray-400">
                  Max {config.tools.max_steps} tool steps per request
                </span>
              </div>

              {config.tools.enabled && (
                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Max Tool Steps
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="12"
                      value={config.tools.max_steps}
                      onInput={(e) => updateConfig('tools.max_steps', parseInt(e.target.value))}
                      class="mt-1 w-full"
                    />
                    <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>0 (disabled)</span>
                      <span>{config.tools.max_steps} steps</span>
                      <span>12 (maximum)</span>
                    </div>
                  </div>

                  <fieldset>
                    <legend class="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Allowed Tool Types
                    </legend>
                    <div class="space-y-2">
                      {[
                        { key: 'allow_shell', label: 'Shell Commands' },
                        { key: 'allow_filesystem', label: 'File System Operations' },
                        { key: 'allow_network', label: 'Network Requests' },
                        { key: 'allow_browser', label: 'Web Browsing' },
                        { key: 'allow_mcp', label: 'MCP Servers' }
                      ].map(({ key, label }) => (
                        <div key={key} class="flex items-center">
                          <input
                            type="checkbox"
                            checked={config.tools[key]}
                            onInput={(e) => updateConfig(`tools.${key}`, e.target.checked)}
                            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <label class="ml-2 block text-sm text-gray-900 dark:text-white">
                            {label}
                          </label>
                        </div>
                      ))}
                    </div>
                  </fieldset>

                  <fieldset>
                    <legend class="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Security Settings
                    </legend>
                    <div class="space-y-2">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Command Timeout (seconds)
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="300"
                          value={config.tools.command_timeout_seconds}
                          onInput={(e) => updateConfig('tools.command_timeout_seconds', parseInt(e.target.value))}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Output Character Limit
                        </label>
                        <input
                          type="number"
                          min="2000"
                          max="200000"
                          value={config.tools.output_char_limit}
                          onInput={(e) => updateConfig('tools.output_char_limit', parseInt(e.target.value))}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                    </div>
                  </fieldset>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Working Directory
                    </label>
                    <input
                      type="text"
                      value={config.tools.working_directory}
                      onInput={(e) => updateConfig('tools.working_directory', e.target.value)}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      placeholder="Path to working directory"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Memory Section */}
          {activeSection === 'memory' && (
            <div class="space-y-6">
              <div class="flex items-center">
                <input
                  type="checkbox"
                  checked={config.memory.enabled}
                  onInput={(e) => updateConfig('memory.enabled', e.target.checked)}
                  class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label class="ml-2 block text-sm font-medium text-gray-900 dark:text-white">
                  Enable Memory System
                </label>
              </div>

              {config.memory.enabled && (
                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Memory Files
                    </label>
                    <div class="mt-2 space-y-2">
                      {config.memory.files.map((file, index) => (
                        <div key={index} class="flex items-center">
                          <input
                            type="text"
                            value={file}
                            onInput={(e) => {
                              const newConfig = { ...config }
                              newConfig.memory.files[index] = e.target.value
                              setConfig(newConfig)
                            }}
                            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                          <button
                            onClick={() => {
                              const newConfig = { ...config }
                              newConfig.memory.files.splice(index, 1)
                              setConfig(newConfig)
                            }}
                            class="ml-2 text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => {
                          const newConfig = { ...config }
                          newConfig.memory.files.push('new_memory.md')
                          setConfig(newConfig)
                        }}
                        class="mt-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                      >
                        Add Memory File
                      </button>
                    </div>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Max Characters Per File
                    </label>
                    <input
                      type="number"
                      min="500"
                      max="50000"
                      value={config.memory.max_chars_per_file}
                      onInput={(e) => updateConfig('memory.max_chars_per_file', parseInt(e.target.value))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div id="statusLine" class="mt-6 text-sm status-line"></div>
    </main>
  )
}

export default SimplifiedSetupPage