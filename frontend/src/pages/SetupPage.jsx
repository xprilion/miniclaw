import { useEffect, useState, useContext } from 'preact/hooks'
import { AppContext } from '../main'
import { api, showStatus } from '../lib/utils'

const SetupPage = () => {
  const { theme } = useContext(AppContext)
  const [config, setConfig] = useState(null)
  const [rawConfig, setRawConfig] = useState('')
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('core')
  const [telegramTest, setTelegramTest] = useState({
    chatId: '',
    message: 'MiniClaw test message'
  })
  const [whatsappTest, setWhatsappTest] = useState({
    contact: '',
    message: 'MiniClaw test message'
  })
  const [selectedProviderId, setSelectedProviderId] = useState('')
  const [editedProvider, setEditedProvider] = useState(null)
  const [modelsByProvider, setModelsByProvider] = useState({})
  const [plugins, setPlugins] = useState([])
  const [memoryFiles, setMemoryFiles] = useState([])
  
  // Form state for different sections
  const [coreForm, setCoreForm] = useState({
    host: '',
    port: '',
    agentName: '',
    maxHistory: '',
    minScore: ''
  })
  
  const [channelsForm, setChannelsForm] = useState({
    telegramToken: '',
    telegramEnabled: false,
    telegramPairing: false,
    telegramChatIds: '',
    whatsappEnabled: false,
    whatsappCommand: 'wacli',
    whatsappContacts: '',
    whatsappPollInterval: '15'
  })
  
  const [toolsForm, setToolsForm] = useState({
    toolsEnabled: false,
    toolsShell: false,
    toolsFilesystem: false,
    toolsNetwork: false,
    toolsBrowser: false,
    toolsMcp: false,
    toolsMaxSteps: '',
    toolsTimeout: '',
    toolsWorkDir: '',
    mcpEnabled: false
  })
  
  const [memoryForm, setMemoryForm] = useState({
    memoryEnabled: false,
    selectedMemoryFiles: [],
    selectedPlugins: []
  })

  const loadConfig = async () => {
    const data = await api('/api/config')
    setConfig(data.config)
    return data.config
  }

  const loadRawConfig = async () => {
    const data = await api('/api/config/raw')
    setRawConfig(data.raw || '')
    return data.raw || ''
  }

  const loadPlugins = async () => {
    const data = await api('/api/plugins')
    setPlugins(data.plugins || [])
    return data.plugins || []
  }

  const loadMemoryFiles = async () => {
    const data = await api('/api/memory')
    const files = Object.keys(data.files || {})
    setMemoryFiles(files)
    return files
  }

  const reloadAll = async () => {
    try {
      const [configData, rawConfigData, pluginsData, memoryFilesData] = await Promise.all([
        loadConfig(),
        loadRawConfig(),
        loadPlugins(),
        loadMemoryFiles()
      ])
      return { config: configData, raw: rawConfigData, plugins: pluginsData, memory: memoryFilesData }
    } catch (error) {
      showStatus(`Failed to load config: ${error.message}`, 'error')
      throw error
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        await reloadAll()
        showStatus('', '')
      } catch (error) {
        showStatus(`Initialization failed: ${error.message}`, 'error')
      } finally {
        setLoading(false)
      }
    }
    
    init()
  }, [])

  // Initialize form state when config loads
  useEffect(() => {
    if (!config) return

    // Core settings
    setCoreForm({
      host: config.server?.host || '',
      port: config.server?.port || '',
      agentName: config.agent?.name || '',
      maxHistory: config.agent?.max_history_messages || '',
      minScore: config.agent?.skill_match_min_score || ''
    })

    // Channels settings
    setChannelsForm({
      telegramToken: config.telegram?.bot_token || '',
      telegramEnabled: !!config.telegram?.enabled,
      telegramPairing: !!config.telegram?.pairing_required,
      telegramChatIds: (config.telegram?.allowed_chat_ids || []).join(', '),
      whatsappEnabled: !!config.channels?.whatsapp_wacli?.enabled,
      whatsappCommand: config.channels?.whatsapp_wacli?.wacli_command || 'wacli',
      whatsappContacts: (config.channels?.whatsapp_wacli?.allowed_contacts || []).join(', '),
      whatsappPollInterval: config.channels?.whatsapp_wacli?.poll_interval_seconds || '15'
    })

    // Tools settings
    setToolsForm({
      toolsEnabled: !!config.tools?.enabled,
      toolsShell: !!config.tools?.allow_shell,
      toolsFilesystem: !!config.tools?.allow_filesystem,
      toolsNetwork: !!config.tools?.allow_network,
      toolsBrowser: !!config.tools?.allow_browser,
      toolsMcp: !!config.tools?.allow_mcp,
      toolsMaxSteps: config.tools?.max_steps || '',
      toolsTimeout: config.tools?.command_timeout_seconds || '',
      toolsWorkDir: config.tools?.working_directory || '',
      mcpEnabled: !!config.mcp?.enabled
    })

    // Memory settings
    setMemoryForm({
      memoryEnabled: !!config.memory?.enabled,
      selectedMemoryFiles: config.memory?.files || [],
      selectedPlugins: config.agent?.enabled_plugins || []
    })

    // Initialize provider editing state
    if (config.providers && config.providers.items && config.providers.items.length > 0) {
      const defaultProviderId = config.providers.default_provider_id || config.providers.items[0]?.id || ''
      setSelectedProviderId(defaultProviderId)
      setEditedProvider(config.providers.items.find(p => p.id === defaultProviderId) || config.providers.items[0] || null)
    }
  }, [config])

  const handleSaveCore = async () => {
    try {
      const updatedConfig = {
        ...config,
        server: {
          ...config.server,
          host: coreForm.host,
          port: parseInt(coreForm.port)
        },
        agent: {
          ...config.agent,
          name: coreForm.agentName,
          max_history_messages: parseInt(coreForm.maxHistory),
          skill_match_min_score: parseInt(coreForm.minScore)
        }
      }

      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      })

      await reloadAll()
      showStatus('Core configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleSaveProviders = async () => {
    try {
      if (!editedProvider) {
        showStatus('No provider selected.', 'error')
        return
      }

      const updatedItems = [...(config.providers.items || [])]
      const selectedIndex = updatedItems.findIndex(p => p.id === selectedProviderId)
      
      if (selectedIndex >= 0) {
        updatedItems[selectedIndex] = { ...editedProvider }
      } else {
        updatedItems.push({ ...editedProvider })
      }

      const updatedConfig = {
        ...config,
        providers: {
          ...config.providers,
          items: updatedItems,
          default_provider_id: config.providers.default_provider_id
        }
      }

      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      })

      await reloadAll()
      showStatus('Provider configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleSaveChannels = async () => {
    try {
      // Validate Telegram settings if enabled
      if (channelsForm.telegramEnabled) {
        if (!channelsForm.telegramToken.trim()) {
          throw new Error('Telegram bot token is required when Telegram is enabled')
        }
      }

      // Validate WhatsApp settings if enabled
      if (channelsForm.whatsappEnabled) {
        if (!channelsForm.whatsappCommand.trim()) {
          throw new Error('wacli command is required when WhatsApp is enabled')
        }
        if (parseInt(channelsForm.whatsappPollInterval) < 5) {
          throw new Error('WhatsApp poll interval must be at least 5 seconds')
        }
      }

      const updatedConfig = {
        ...config,
        telegram: {
          ...config.telegram,
          bot_token: channelsForm.telegramToken,
          enabled: channelsForm.telegramEnabled,
          pairing_required: channelsForm.telegramPairing,
          allowed_chat_ids: channelsForm.telegramChatIds.split(',').map(id => id.trim()).filter(id => id)
        },
        channels: {
          ...config.channels,
          whatsapp_wacli: {
            ...(config.channels?.whatsapp_wacli || {}),
            enabled: channelsForm.whatsappEnabled,
            wacli_command: channelsForm.whatsappCommand,
            allowed_contacts: channelsForm.whatsappContacts.split(',').map(contact => contact.trim()).filter(contact => contact),
            poll_interval_seconds: parseInt(channelsForm.whatsappPollInterval) || 15
          }
        }
      }

      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      })

      await reloadAll()
      showStatus('Channel configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleSaveTools = async () => {
    try {
      const updatedConfig = {
        ...config,
        tools: {
          ...config.tools,
          enabled: toolsForm.toolsEnabled,
          allow_shell: toolsForm.toolsShell,
          allow_filesystem: toolsForm.toolsFilesystem,
          allow_network: toolsForm.toolsNetwork,
          allow_browser: toolsForm.toolsBrowser,
          allow_mcp: toolsForm.toolsMcp,
          max_steps: parseInt(toolsForm.toolsMaxSteps),
          command_timeout_seconds: parseInt(toolsForm.toolsTimeout),
          working_directory: toolsForm.toolsWorkDir
        },
        mcp: {
          ...config.mcp,
          enabled: toolsForm.mcpEnabled
        }
      }

      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      })

      await reloadAll()
      showStatus('Tools configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleSaveMemory = async () => {
    try {
      const updatedConfig = {
        ...config,
        memory: {
          ...config.memory,
          enabled: memoryForm.memoryEnabled,
          files: memoryForm.selectedMemoryFiles
        },
        agent: {
          ...config.agent,
          enabled_plugins: memoryForm.selectedPlugins
        }
      }

      await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      })

      await reloadAll()
      showStatus('Memory configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleSaveRawConfig = async () => {
    try {
      await api('/api/config/raw', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw: rawConfig })
      })

      // Reload config to verify
      await reloadAll()
      showStatus('Configuration saved.', 'success')
    } catch (error) {
      showStatus(`Save failed: ${error.message}`, 'error')
    }
  }

  const handleTestTelegram = async () => {
    try {
      let chatId = telegramTest.chatId.trim();
      
      // If no chat ID provided, use the bound chat ID if available
      if (!chatId && config?.telegram?.allowed_chat_ids?.[0]) {
        chatId = config.telegram.allowed_chat_ids[0];
      }
      
      if (!chatId) {
        throw new Error('Chat ID is required')
      }

      await api('/api/telegram/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          message: telegramTest.message
        })
      })

      showStatus('Test message sent to Telegram.', 'success')
    } catch (error) {
      showStatus(`Telegram test failed: ${error.message}`, 'error')
    }
  }

  const handleRestartTelegram = async () => {
    try {
      await api('/api/telegram/restart', {
        method: 'POST'
      })

      showStatus('Telegram service restarted.', 'success')
      // Reload config to get updated status
      await reloadAll()
    } catch (error) {
      showStatus(`Restart failed: ${error.message}`, 'error')
    }
  }

  const handleUnbindTelegram = async () => {
    try {
      await api('/api/telegram/unbind', {
        method: 'POST'
      })

      showStatus('Telegram unbound successfully.', 'success')
      // Reload config to get updated status
      await reloadAll()
    } catch (error) {
      showStatus(`Unbind failed: ${error.message}`, 'error')
    }
  }

  const handleTestWhatsApp = async () => {
    try {
      const contact = whatsappTest.contact.trim();
      
      if (!contact) {
        throw new Error('Contact is required')
      }

      await api('/api/whatsapp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact: contact,
          message: whatsappTest.message
        })
      })

      showStatus('Test message sent to WhatsApp.', 'success')
    } catch (error) {
      showStatus(`WhatsApp test failed: ${error.message}`, 'error')
    }
  }

  const handleRestartWhatsApp = async () => {
    try {
      await api('/api/whatsapp/restart', {
        method: 'POST'
      })

      showStatus('WhatsApp service restarted.', 'success')
      // Reload config to get updated status
      await reloadAll()
    } catch (error) {
      showStatus(`Restart failed: ${error.message}`, 'error')
    }
  }

  const handleRefresh = async () => {
    try {
      await reloadAll()
      showStatus('Configuration refreshed.', 'success')
    } catch (error) {
      showStatus(`Refresh failed: ${error.message}`, 'error')
    }
  }

  const handleAddProvider = () => {
    const newProvider = {
      id: `provider_${Date.now()}`,
      name: 'New Provider',
      type: 'ollama',
      base_url: 'http://localhost:11434',
      model: 'llama2',
      temperature: 0.7,
      timeout_seconds: 120,
      verify_tls: true,
      api_key: '',
      system_prompt_override: '',
      enabled: false
    }
    
    setEditedProvider(newProvider)
    setSelectedProviderId(newProvider.id)
  }

  const handleDeleteProvider = () => {
    if (!selectedProviderId || !config || !config.providers || !config.providers.items) return
    
    const updatedItems = config.providers.items.filter(p => p.id !== selectedProviderId)
    const updatedConfig = {
      ...config,
      providers: {
        ...config.providers,
        items: updatedItems
      }
    }
    
    setConfig(updatedConfig)
    if (updatedItems.length > 0) {
      setSelectedProviderId(updatedItems[0].id)
      setEditedProvider(updatedItems[0])
    } else {
      setSelectedProviderId('')
      setEditedProvider(null)
    }
  }

  const handleProviderChange = (field, value) => {
    if (!editedProvider) return
    
    const updatedProvider = { ...editedProvider }
    
    // Handle special cases for different field types
    if (field === 'enabled' || field === 'verify_tls') {
      updatedProvider[field] = Boolean(value)
    } else if (field === 'temperature' || field === 'timeout_seconds') {
      updatedProvider[field] = parseFloat(value) || 0
    } else if (field === 'id') {
      // Sanitize provider ID
      const sanitized = String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]/g, '')
      updatedProvider[field] = sanitized
    } else {
      updatedProvider[field] = value
    }
    
    setEditedProvider(updatedProvider)
  }

  const handleProviderSelect = (providerId) => {
    if (!config || !config.providers || !config.providers.items) return
    
    const provider = config.providers.items.find(p => p.id === providerId)
    if (provider) {
      setSelectedProviderId(providerId)
      setEditedProvider({ ...provider })
    }
  }

  // Toggle memory file selection
  const toggleMemoryFile = (file) => {
    setMemoryForm(prev => {
      const selected = [...prev.selectedMemoryFiles]
      const index = selected.indexOf(file)
      if (index >= 0) {
        selected.splice(index, 1)
      } else {
        selected.push(file)
      }
      return { ...prev, selectedMemoryFiles: selected }
    })
  }

  // Toggle plugin selection
  const togglePlugin = (pluginId) => {
    setMemoryForm(prev => {
      const selected = [...prev.selectedPlugins]
      const index = selected.indexOf(pluginId)
      if (index >= 0) {
        selected.splice(index, 1)
      } else {
        selected.push(pluginId)
      }
      return { ...prev, selectedPlugins: selected }
    })
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
       {/* Tab Navigation */}
       <div class="mb-6 flex border-b border-gray-200 dark:border-gray-700">
         <button
           onClick={() => setActiveTab('core')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'core'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Core
         </button>
         <button
           onClick={() => setActiveTab('providers')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'providers'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Providers
         </button>
         <button
           onClick={() => setActiveTab('channels')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'channels'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Channels
         </button>
         <button
           onClick={() => setActiveTab('tools')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'tools'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Tools & MCP
         </button>
         <button
           onClick={() => setActiveTab('memory')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'memory'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Memory & Plugins
         </button>
         <button
           onClick={() => setActiveTab('raw')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'raw'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Raw Config
         </button>
         <button
           onClick={() => setActiveTab('telegram')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'telegram'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           Telegram
         </button>
         <button
           onClick={() => setActiveTab('whatsapp')}
           class={`py-2 px-4 text-sm font-medium ${
             activeTab === 'whatsapp'
               ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
               : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
           }`}
         >
           WhatsApp
         </button>
       </div>

      {/* Core Panel */}
      {activeTab === 'core' && (
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Core Config</h2>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Configure basic server and agent settings.
            </p>
            
            <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label for="cfgHost" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Web Host
                </label>
                <input
                  id="cfgHost"
                  value={coreForm.host}
                  onInput={(e) => setCoreForm(prev => ({ ...prev, host: e.target.value }))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div>
                <label for="cfgPort" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Web Port
                </label>
                <input
                  id="cfgPort"
                  type="number"
                  min="1"
                  max="65535"
                  value={coreForm.port}
                  onInput={(e) => setCoreForm(prev => ({ ...prev, port: e.target.value }))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>

            <div class="mt-4">
              <label for="cfgAgentName" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Agent Name
              </label>
              <input
                id="cfgAgentName"
                value={coreForm.agentName}
                onInput={(e) => setCoreForm(prev => ({ ...prev, agentName: e.target.value }))}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div class="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label for="cfgMaxHistory" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Max History Messages
                </label>
                <input
                  id="cfgMaxHistory"
                  type="number"
                  min="0"
                  value={coreForm.maxHistory}
                  onInput={(e) => setCoreForm(prev => ({ ...prev, maxHistory: e.target.value }))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div>
                <label for="cfgMinScore" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Skill Match Min Score
                </label>
                <input
                  id="cfgMinScore"
                  type="number"
                  min="0"
                  value={coreForm.minScore}
                  onInput={(e) => setCoreForm(prev => ({ ...prev, minScore: e.target.value }))}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>

            <div class="mt-6">
              <button
                onClick={handleSaveCore}
                class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Save Core Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Providers Panel */}
      {activeTab === 'providers' && (
        <div class="space-y-6">
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 class="text-lg font-medium text-gray-900 dark:text-white">Model Providers</h2>
                  <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Configure AI model providers and credentials.
                  </p>
                </div>
                <div class="mt-3 flex space-x-2 sm:mt-0">
                  <button
                    onClick={handleAddProvider}
                    class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                  >
                    Add Provider
                  </button>
                  <button
                    onClick={handleDeleteProvider}
                    disabled={!selectedProviderId}
                    class="inline-flex items-center rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 shadow-sm hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:border-red-600 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
                  >
                    Delete Provider
                  </button>
                </div>
              </div>

              <div class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Provider List */}
                <div class="lg:col-span-1">
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Providers
                  </label>
                  <div class="border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden">
                    {(config?.providers?.items || []).map((provider) => (
                      <div
                        key={provider.id}
                        onClick={() => handleProviderSelect(provider.id)}
                        class={`p-3 cursor-pointer border-b border-gray-200 dark:border-gray-700 last:border-b-0 ${
                          selectedProviderId === provider.id
                            ? 'bg-primary-50 dark:bg-primary-900/30'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        <div class="flex items-center justify-between">
                          <div>
                            <div class="font-medium text-gray-900 dark:text-white">
                              {provider.name}
                            </div>
                            <div class="text-sm text-gray-500 dark:text-gray-400">
                              {provider.type} • {provider.model}
                            </div>
                          </div>
                          {provider.enabled && (
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                              Enabled
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                    {(!config?.providers?.items || config.providers.items.length === 0) && (
                      <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                        No providers configured
                      </div>
                    )}
                  </div>
                </div>

                {/* Provider Editor */}
                <div class="lg:col-span-2">
                  {editedProvider ? (
                    <div class="space-y-4">
                      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div>
                          <label for="providerId" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Provider ID
                          </label>
                          <input
                            id="providerId"
                            value={editedProvider.id}
                            onInput={(e) => handleProviderChange('id', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        </div>
                        <div>
                          <label for="providerName" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Display Name
                          </label>
                          <input
                            id="providerName"
                            value={editedProvider.name}
                            onInput={(e) => handleProviderChange('name', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        </div>
                      </div>

                      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div>
                          <label for="providerType" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Type
                          </label>
                          <select
                            id="providerType"
                            value={editedProvider.type}
                            onChange={(e) => handleProviderChange('type', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          >
                            <option value="ollama">Ollama</option>
                            <option value="openai_compatible">OpenAI Compatible</option>
                            <option value="litellm">LiteLLM</option>
                            <option value="openrouter">OpenRouter</option>
                          </select>
                        </div>
                        <div>
                          <label for="providerModel" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Default Model
                          </label>
                          <input
                            id="providerModel"
                            value={editedProvider.model}
                            onInput={(e) => handleProviderChange('model', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        </div>
                      </div>

                      <div>
                        <label for="providerBaseUrl" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Base URL
                        </label>
                        <input
                          id="providerBaseUrl"
                          value={editedProvider.base_url}
                          onInput={(e) => handleProviderChange('base_url', e.target.value)}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
                        <div>
                          <label for="providerTemperature" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Temperature
                          </label>
                          <input
                            id="providerTemperature"
                            type="number"
                            step="0.1"
                            min="0"
                            max="2"
                            value={editedProvider.temperature}
                            onInput={(e) => handleProviderChange('temperature', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        </div>
                        <div>
                          <label for="providerTimeout" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Timeout (seconds)
                          </label>
                          <input
                            id="providerTimeout"
                            type="number"
                            min="1"
                            value={editedProvider.timeout_seconds}
                            onInput={(e) => handleProviderChange('timeout_seconds', e.target.value)}
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        </div>
                        <div class="flex items-end">
                          <div class="flex items-center">
                            <input
                              id="providerVerifyTls"
                              type="checkbox"
                              checked={editedProvider.verify_tls}
                              onChange={(e) => handleProviderChange('verify_tls', e.target.checked)}
                              class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                            />
                            <label for="providerVerifyTls" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                              Verify TLS
                            </label>
                          </div>
                        </div>
                      </div>

                      <div>
                        <label for="providerApiKey" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          API Key (if required)
                        </label>
                        <input
                          id="providerApiKey"
                          type="password"
                          value={editedProvider.api_key}
                          onInput={(e) => handleProviderChange('api_key', e.target.value)}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                      </div>

                      <div>
                        <label for="providerSystemPrompt" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          System Prompt Override (optional)
                        </label>
                        <textarea
                          id="providerSystemPrompt"
                          rows={3}
                          value={editedProvider.system_prompt_override}
                          onInput={(e) => handleProviderChange('system_prompt_override', e.target.value)}
                          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        ></textarea>
                      </div>

                      <div class="flex items-center">
                        <input
                          id="providerEnabled"
                          type="checkbox"
                          checked={editedProvider.enabled}
                          onChange={(e) => handleProviderChange('enabled', e.target.checked)}
                          class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                        />
                        <label for="providerEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                          Provider Enabled
                        </label>
                      </div>
                    </div>
                  ) : (
                    <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                      Select a provider to edit or add a new one
                    </div>
                  )}
                </div>
              </div>

              {/* Default Provider Selector */}
              <div class="mt-6">
                <label for="cfgDefaultProvider" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Provider
                </label>
                <select
                  id="cfgDefaultProvider"
                  value={config?.providers?.default_provider_id || ''}
                  onChange={(e) => {
                    const updatedConfig = {
                      ...config,
                      providers: {
                        ...config.providers,
                        default_provider_id: e.target.value
                      }
                    }
                    setConfig(updatedConfig)
                  }}
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  {(config?.providers?.items || []).map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name} ({provider.type})
                    </option>
                  ))}
                </select>
              </div>

              <div class="mt-6">
                <button
                  onClick={handleSaveProviders}
                  class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                >
                  Save Provider Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Channels Panel */}
      {activeTab === 'channels' && (
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Channel Integration</h2>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Configure how MiniClaw communicates with users.
            </p>
            
            <div class="mt-6 space-y-6">
              {/* Telegram Settings */}
              <div>
                <h3 class="text-md font-medium text-gray-900 dark:text-white">Telegram</h3>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Enable two-way communication with Telegram users.
                </p>
                
                <div class="mt-4 space-y-4">
                  <div class="flex items-center">
                    <input
                      id="cfgTelegramEnabled"
                      type="checkbox"
                      checked={channelsForm.telegramEnabled}
                      onChange={(e) => setChannelsForm(prev => ({ ...prev, telegramEnabled: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgTelegramEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Enable Telegram Integration
                    </label>
                  </div>
                  
                  <div>
                    <label for="cfgTelegramToken" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Bot Token
                    </label>
                    <input
                      id="cfgTelegramToken"
                      type="password"
                      value={channelsForm.telegramToken}
                      onInput={(e) => setChannelsForm(prev => ({ ...prev, telegramToken: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Obtain from @BotFather on Telegram.
                    </p>
                  </div>
                  
                  <div class="flex items-center">
                    <input
                      id="cfgTelegramPairing"
                      type="checkbox"
                      checked={channelsForm.telegramPairing}
                      onChange={(e) => setChannelsForm(prev => ({ ...prev, telegramPairing: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgTelegramPairing" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Require Pairing Code
                    </label>
                  </div>
                  
                  <div>
                    <label for="cfgTelegramChatIds" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Allowed Chat IDs (comma-separated)
                    </label>
                    <input
                      id="cfgTelegramChatIds"
                      value={channelsForm.telegramChatIds}
                      onInput={(e) => setChannelsForm(prev => ({ ...prev, telegramChatIds: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Specific chats that can interact with the bot. Leave empty to allow all chats when pairing is disabled.
                    </p>
                  </div>
                </div>
              </div>
              
              {/* WhatsApp Settings */}
              <div>
                <h3 class="text-md font-medium text-gray-900 dark:text-white">WhatsApp (wacli)</h3>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Enable two-way communication with WhatsApp contacts using wacli.
                </p>
                
                <div class="mt-4 space-y-4">
                  <div class="flex items-center">
                    <input
                      id="cfgWhatsAppEnabled"
                      type="checkbox"
                      checked={channelsForm.whatsappEnabled}
                      onChange={(e) => setChannelsForm(prev => ({ ...prev, whatsappEnabled: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgWhatsAppEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Enable WhatsApp Integration
                    </label>
                  </div>
                  
                  <div>
                    <label for="cfgWhatsAppCommand" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      wacli Command
                    </label>
                    <input
                      id="cfgWhatsAppCommand"
                      value={channelsForm.whatsappCommand}
                      onInput={(e) => setChannelsForm(prev => ({ ...prev, whatsappCommand: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      The command to run wacli. Make sure it's in your PATH.
                    </p>
                  </div>
                  
                  <div>
                    <label for="cfgWhatsAppContacts" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Allowed Contacts (comma-separated)
                    </label>
                    <input
                      id="cfgWhatsAppContacts"
                      value={channelsForm.whatsappContacts}
                      onInput={(e) => setChannelsForm(prev => ({ ...prev, whatsappContacts: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Phone numbers that can interact with the bot. Leave empty to allow all contacts.
                    </p>
                  </div>
                  
                  <div>
                    <label for="cfgWhatsAppPollInterval" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Poll Interval (seconds)
                    </label>
                    <input
                      id="cfgWhatsAppPollInterval"
                      type="number"
                      min="5"
                      max="300"
                      value={channelsForm.whatsappPollInterval}
                      onInput={(e) => setChannelsForm(prev => ({ ...prev, whatsappPollInterval: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      How often to check for new messages (5-300 seconds).
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Email Settings */}
              <div>
                <h3 class="text-md font-medium text-gray-900 dark:text-white">Email</h3>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Email integration coming soon.
                </p>
              </div>
            </div>
            
            <div class="mt-6">
              <button
                onClick={handleSaveChannels}
                class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Save Channel Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tools & MCP Panel */}
      {activeTab === 'tools' && (
        <div class="space-y-6">
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Tool Access Control</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure which tools the agent can use.
              </p>
              
              <div class="mt-6 space-y-4">
                <div class="flex items-center">
                  <input
                    id="cfgToolsEnabled"
                    type="checkbox"
                    checked={toolsForm.toolsEnabled}
                    onChange={(e) => setToolsForm(prev => ({ ...prev, toolsEnabled: e.target.checked }))}
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                  />
                  <label for="cfgToolsEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                    Enable Tools
                  </label>
                </div>
                
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div class="flex items-center">
                    <input
                      id="cfgToolsShell"
                      type="checkbox"
                      checked={toolsForm.toolsShell}
                      onChange={(e) => setToolsForm(prev => ({ ...prev, toolsShell: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgToolsShell" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Allow Shell Commands
                    </label>
                  </div>
                  
                  <div class="flex items-center">
                    <input
                      id="cfgToolsFilesystem"
                      type="checkbox"
                      checked={toolsForm.toolsFilesystem}
                      onChange={(e) => setToolsForm(prev => ({ ...prev, toolsFilesystem: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgToolsFilesystem" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Allow Filesystem Access
                    </label>
                  </div>
                  
                  <div class="flex items-center">
                    <input
                      id="cfgToolsNetwork"
                      type="checkbox"
                      checked={toolsForm.toolsNetwork}
                      onChange={(e) => setToolsForm(prev => ({ ...prev, toolsNetwork: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgToolsNetwork" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Allow Network Requests
                    </label>
                  </div>
                  
                  <div class="flex items-center">
                    <input
                      id="cfgToolsBrowser"
                      type="checkbox"
                      checked={toolsForm.toolsBrowser}
                      onChange={(e) => setToolsForm(prev => ({ ...prev, toolsBrowser: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgToolsBrowser" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Allow Browser Operations
                    </label>
                  </div>
                  
                  <div class="flex items-center">
                    <input
                      id="cfgToolsMcp"
                      type="checkbox"
                      checked={toolsForm.toolsMcp}
                      onChange={(e) => setToolsForm(prev => ({ ...prev, toolsMcp: e.target.checked }))}
                      class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="cfgToolsMcp" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                      Allow MCP Integration
                    </label>
                  </div>
                </div>
                
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label for="cfgToolsMaxSteps" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Max Tool Steps Per Request
                    </label>
                    <input
                      id="cfgToolsMaxSteps"
                      type="number"
                      min="1"
                      max="10"
                      value={toolsForm.toolsMaxSteps}
                      onInput={(e) => setToolsForm(prev => ({ ...prev, toolsMaxSteps: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                  
                  <div>
                    <label for="cfgToolsTimeout" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Command Timeout (seconds)
                    </label>
                    <input
                      id="cfgToolsTimeout"
                      type="number"
                      min="1"
                      max="300"
                      value={toolsForm.toolsTimeout}
                      onInput={(e) => setToolsForm(prev => ({ ...prev, toolsTimeout: e.target.value }))}
                      class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                </div>
                
                <div>
                  <label for="cfgToolsWorkDir" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Working Directory
                  </label>
                  <input
                    id="cfgToolsWorkDir"
                    value={toolsForm.toolsWorkDir}
                    onInput={(e) => setToolsForm(prev => ({ ...prev, toolsWorkDir: e.target.value }))}
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>
              
              <div class="mt-6">
                <button
                  onClick={handleSaveTools}
                  class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                >
                  Save Tool Settings
                </button>
              </div>
            </div>
          </div>
          
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">MCP Servers</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure Model Context Protocol servers.
              </p>
              
              <div class="mt-4">
                <div class="flex items-center">
                  <input
                    id="cfgMcpEnabled"
                    type="checkbox"
                    checked={toolsForm.mcpEnabled}
                    onChange={(e) => setToolsForm(prev => ({ ...prev, mcpEnabled: e.target.checked }))}
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                  />
                  <label for="cfgMcpEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                    Enable MCP Integration
                  </label>
                </div>
                
                <div class="mt-4">
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    MCP server configuration coming soon in this UI. For now, configure via Raw Config.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Memory & Plugins Panel */}
      {activeTab === 'memory' && (
        <div class="space-y-6">
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Memory Files</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure which memory files the agent can access.
              </p>
              
              <div class="mt-6">
                <div class="flex items-center">
                  <input
                    id="cfgMemoryEnabled"
                    type="checkbox"
                    checked={memoryForm.memoryEnabled}
                    onChange={(e) => setMemoryForm(prev => ({ ...prev, memoryEnabled: e.target.checked }))}
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                  />
                  <label for="cfgMemoryEnabled" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                    Enable Memory Access
                  </label>
                </div>
                
                <div class="mt-4">
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Select Memory Files
                  </label>
                  <div class="mt-2 border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden max-h-48 overflow-y-auto">
                    {memoryFiles.map((file) => (
                      <div 
                        key={file} 
                        class="flex items-center px-4 py-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <input
                          id={`memory-${file}`}
                          type="checkbox"
                          checked={memoryForm.selectedMemoryFiles.includes(file)}
                          onChange={() => toggleMemoryFile(file)}
                          class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                        />
                        <label for={`memory-${file}`} class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                          {file}
                        </label>
                      </div>
                    ))}
                  </div>
                  <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Select which memory files to make available to the agent.
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
            <div class="px-4 py-5 sm:p-6">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Plugins</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Enable or disable plugins that extend agent functionality.
              </p>
              
              <div class="mt-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Enabled Plugins
                </label>
                <div class="mt-2 border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden max-h-48 overflow-y-auto">
                  {plugins.map((plugin) => (
                    <div 
                      key={plugin.id} 
                      class="flex items-start px-4 py-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <input
                        id={`plugin-${plugin.id}`}
                        type="checkbox"
                        checked={memoryForm.selectedPlugins.includes(plugin.id)}
                        onChange={() => togglePlugin(plugin.id)}
                        class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 mt-1"
                      />
                      <div class="ml-2">
                        <label for={`plugin-${plugin.id}`} class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          {plugin.name}
                        </label>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {plugin.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Select which plugins to enable for the agent.
                  </p>
              </div>
              
              <div class="mt-6">
                <button
                  onClick={handleSaveMemory}
                  class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                >
                  Save Memory & Plugin Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Raw Config Panel */}
      {activeTab === 'raw' && (
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="text-lg font-medium text-gray-900 dark:text-white">Raw Configuration</h2>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Edit the raw JSON configuration. Changes take effect immediately.
                </p>
              </div>
              <div class="mt-3 flex space-x-2 sm:mt-0">
                <button
                  onClick={handleRefresh}
                  class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                >
                  Refresh
                </button>
              </div>
            </div>
            
            <div class="mt-4">
              <textarea
                rows={25}
                value={rawConfig}
                onInput={(e) => setRawConfig(e.target.value)}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white font-mono text-sm"
                spellcheck="false"
              ></textarea>
            </div>
            
            <div class="mt-4 flex flex-wrap gap-2">
              <button
                onClick={handleSaveRawConfig}
                class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Save Configuration
              </button>
            </div>
            <div id="statusLine" class="mt-4 text-sm status-line"></div>
          </div>
        </div>
      )}

       {/* Telegram Panel */}
       {activeTab === 'telegram' && (
         <div class="space-y-6">
           <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
             <div class="px-4 py-5 sm:p-6">
               <h2 class="text-lg font-medium text-gray-900 dark:text-white">Telegram Settings</h2>
               <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                 Configure Telegram integration.
               </p>
               
               <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Bot Token
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.telegram?.bot_token ? '••••••••' : 'Not set'}
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Enabled
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.telegram?.enabled ? 'Yes' : 'No'}
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Pairing Required
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.telegram?.pairing_required ? 'Yes' : 'No'}
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Allowed Chat IDs
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.telegram?.allowed_chat_ids?.length || 0} configured
                   </div>
                 </div>
               </div>
             </div>
           </div>

           <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
             <div class="px-4 py-5 sm:p-6">
               <h2 class="text-lg font-medium text-gray-900 dark:text-white">Telegram Actions</h2>
               <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                 Manage your Telegram integration.
               </p>
               
               <div class="mt-6 space-y-4">
                 <div>
                   <label htmlFor="testChatId" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Test Message
                   </label>
                   <div class="mt-2 flex flex-col sm:flex-row gap-2">
                     <input
                       id="testChatId"
                       type="text"
                       value={telegramTest.chatId}
                       onInput={(e) => setTelegramTest(prev => ({ ...prev, chatId: e.target.value }))}
                       placeholder={config?.telegram?.allowed_chat_ids?.[0] || "Chat ID"}
                       class="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                     />
                     <input
                       type="text"
                       value={telegramTest.message}
                       onInput={(e) => setTelegramTest(prev => ({ ...prev, message: e.target.value }))}
                       placeholder="Message"
                       class="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                     />
                     <button
                       onClick={handleTestTelegram}
                       class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                     >
                       Send Test
                     </button>
                   </div>
                   {config?.telegram?.allowed_chat_ids?.[0] && (
                     <div class="mt-2">
                       <button
                         onClick={() => setTelegramTest(prev => ({ ...prev, chatId: config.telegram.allowed_chat_ids[0] }))}
                         class="text-sm text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300"
                       >
                         Use bound chat ID ({config.telegram.allowed_chat_ids[0]})
                       </button>
                     </div>
                   )}
                 </div>
                 
                 <div class="flex flex-wrap gap-2 pt-4">
                   <button
                     onClick={handleRestartTelegram}
                     class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                   >
                     Restart Telegram Service
                   </button>
                   <button
                     onClick={handleUnbindTelegram}
                     class="inline-flex items-center rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 shadow-sm hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:border-red-600 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
                   >
                     Unbind Telegram
                   </button>
                 </div>
               </div>
             </div>
           </div>
         </div>
       )}

       {/* WhatsApp Panel */}
       {activeTab === 'whatsapp' && (
         <div class="space-y-6">
           <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
             <div class="px-4 py-5 sm:p-6">
               <h2 class="text-lg font-medium text-gray-900 dark:text-white">WhatsApp Settings</h2>
               <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                 Configure WhatsApp integration using wacli.
               </p>
               
               <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Enabled
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.channels?.whatsapp_wacli?.enabled ? 'Yes' : 'No'}
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     wacli Command
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.channels?.whatsapp_wacli?.wacli_command || 'wacli'}
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Poll Interval
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.channels?.whatsapp_wacli?.poll_interval_seconds || 15} seconds
                   </div>
                 </div>
                 
                 <div>
                   <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Allowed Contacts
                   </label>
                   <div class="mt-1 text-sm text-gray-900 dark:text-white">
                     {config?.channels?.whatsapp_wacli?.allowed_contacts?.length || 0} configured
                   </div>
                 </div>
               </div>
             </div>
           </div>

           <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
             <div class="px-4 py-5 sm:p-6">
               <h2 class="text-lg font-medium text-gray-900 dark:text-white">WhatsApp Actions</h2>
               <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                 Manage your WhatsApp integration.
               </p>
               
               <div class="mt-6 space-y-4">
                 <div>
                   <label htmlFor="testWhatsAppContact" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                     Test Message
                   </label>
                   <div class="mt-2 flex flex-col sm:flex-row gap-2">
                     <input
                       id="testWhatsAppContact"
                       type="text"
                       value={whatsappTest?.contact || ''}
                       onInput={(e) => setWhatsappTest(prev => ({ ...prev, contact: e.target.value }))}
                       placeholder="Contact (phone number)"
                       class="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                     />
                     <input
                       type="text"
                       value={whatsappTest?.message || 'MiniClaw test message'}
                       onInput={(e) => setWhatsappTest(prev => ({ ...prev, message: e.target.value }))}
                       placeholder="Message"
                       class="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                     />
                     <button
                       onClick={handleTestWhatsApp}
                       class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                     >
                       Send Test
                     </button>
                   </div>
                 </div>
                 
                 <div class="flex flex-wrap gap-2 pt-4">
                   <button
                     onClick={handleRestartWhatsApp}
                     class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                   >
                     Restart WhatsApp Service
                   </button>
                 </div>
               </div>
             </div>
           </div>
         </div>
       )}
    </main>
  )
}

export default SetupPage