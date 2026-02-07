import { useEffect, useState, useCallback } from 'preact/hooks'
import { api, showStatus } from '../lib/utils'

const SkillsPage = () => {
  const [config, setConfig] = useState(null)
  const [skills, setSkills] = useState([])
  const [selectedSkillId, setSelectedSkillId] = useState('')
  const [loading, setLoading] = useState(true)
  const [formData, setFormData] = useState({
    id: '',
    content: '# New Skill\n\nkeywords: \n\nGuidelines...\n',
    enabled: false
  })
  const [minScore, setMinScore] = useState(2)

  const loadConfig = useCallback(async () => {
    const data = await api('/api/config')
    setConfig(data.config)
    setMinScore(data.config.agent.skill_match_min_score || 2)
    return data.config
  }, [])

  const loadSkills = useCallback(async () => {
    const data = await api('/api/skills')
    setSkills(data.skills || [])
    return data.skills || []
  }, [])

  const reloadAll = useCallback(async () => {
    try {
      const [configData, skillsData] = await Promise.all([
        loadConfig(),
        loadSkills()
      ])
      return { config: configData, skills: skillsData }
    } catch (error) {
      showStatus(`Failed to load data: ${error.message}`, 'error')
      throw error
    }
  }, [loadConfig, loadSkills])

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
  }, [reloadAll])

  const enabledSet = () => {
    return new Set((config?.agent?.enabled_skills || []).map(item => String(item)))
  }

  const selectSkill = (skillId) => {
    const skill = skills.find(item => item.id === skillId)
    if (!skill) return
    
    setSelectedSkillId(skill.id)
    setFormData({
      id: skill.id,
      content: skill.content || '',
      enabled: enabledSet().has(skill.id)
    })
  }

  const clearEditor = () => {
    setSelectedSkillId('')
    setFormData({
      id: '',
      content: '# New Skill\n\nkeywords: \n\nGuidelines...\n',
      enabled: false
    })
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSaveSkill = async () => {
    try {
      if (!formData.id.trim()) {
        throw new Error('Skill ID is required')
      }
      if (!formData.content.trim()) {
        throw new Error('Skill markdown content is required')
      }

      // Save the skill content
      await api('/api/skills/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          id: formData.id.trim(), 
          content: formData.content 
        })
      })

      // Update settings (enabled status)
      const enabled = enabledSet()
      if (formData.enabled) {
        enabled.add(formData.id.trim())
      } else {
        enabled.delete(formData.id.trim())
      }

      await api('/api/skills/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled_skills: Array.from(enabled),
          skill_match_min_score: minScore
        })
      })

      // Reload data
      await reloadAll()
      setSelectedSkillId(formData.id.trim())
      selectSkill(formData.id.trim())
      showStatus('Skill saved.', 'success')
    } catch (error) {
      showStatus(`Save skill failed: ${error.message}`, 'error')
    }
  }

  const handleDeleteSkill = async () => {
    try {
      if (!formData.id.trim()) {
        throw new Error('Skill ID is required')
      }

      // Delete the skill
      await api('/api/skills/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: formData.id.trim() })
      })

      // Update enabled skills if needed
      const enabled = enabledSet()
      if (enabled.has(formData.id.trim())) {
        enabled.delete(formData.id.trim())
        await api('/api/skills/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            enabled_skills: Array.from(enabled),
            skill_match_min_score: minScore
          })
        })
      }

      // Reload data
      await reloadAll()
      clearEditor()
      showStatus('Skill deleted.', 'success')
    } catch (error) {
      showStatus(`Delete skill failed: ${error.message}`, 'error')
    }
  }

  const handleSaveSettings = async () => {
    try {
      const enabled = enabledSet()
      
      // Update settings
      const data = await api('/api/skills/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled_skills: Array.from(enabled),
          skill_match_min_score: minScore
        })
      })

      setConfig(prev => ({
        ...prev,
        agent: {
          ...prev.agent,
          enabled_skills: data.settings.enabled_skills || [],
          skill_match_min_score: data.settings.skill_match_min_score || minScore
        }
      }))

      showStatus('Skill settings updated.', 'success')
    } catch (error) {
      showStatus(`Skill settings update failed: ${error.message}`, 'error')
    }
  }

  const handleRefresh = async () => {
    try {
      await reloadAll()
      showStatus('Skills refreshed.', 'success')
    } catch (error) {
      showStatus(`Refresh failed: ${error.message}`, 'error')
    }
  }

  if (loading) {
    return (
      <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="text-center py-12">
          <div class="miniclaw-loading-placeholder">
            <span>Loading skills...</span>
          </div>
        </div>
      </main>
    )
  }

  const enabledSkills = enabledSet()

  return (
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Skill Files Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Skill Files</h2>
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
            <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Click a skill to edit. Files are stored as markdown.
            </p>
            <div 
              id="skillsList" 
              class="mt-4 h-96 min-h-96 overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900"
            >
              {skills.length === 0 ? (
                <div class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                  No skills yet.
                </div>
              ) : (
                skills.map(skill => {
                  const isSelected = selectedSkillId === skill.id
                  const isEnabled = enabledSkills.has(skill.id)
                  
                  return (
                    <div 
                      key={skill.id}
                      class={`feed-item ${isSelected ? 'selected' : ''} cursor-pointer`}
                      onClick={() => selectSkill(skill.id)}
                    >
                      <div class="feed-meta">
                        {skill.id} {isEnabled ? '(enabled)' : '(disabled)'}
                      </div>
                      <div class="feed-body">
                        {skill.title || skill.id}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>

        {/* Editor Card */}
        <div class="overflow-hidden rounded-lg bg-white shadow dark:bg-gray-800">
          <div class="px-4 py-5 sm:p-6">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Editor</h2>
            
            <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="skillIdInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Skill ID
                </label>
                <input
                  id="skillIdInput"
                  value={formData.id}
                  onInput={(e) => handleInputChange('id', e.target.value)}
                  placeholder="example: billing"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div class="flex items-end">
                <div class="flex items-center">
                  <input
                    id="skillEnabledInput"
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) => handleInputChange('enabled', e.target.checked)}
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:ring-offset-gray-800"
                  />
                  <label htmlFor="skillEnabledInput" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                    Enabled for matching
                  </label>
                </div>
              </div>
            </div>

            <div class="mt-4">
              <label htmlFor="skillMatchMinScore" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Skill Match Min Score (global)
              </label>
              <input
                id="skillMatchMinScore"
                type="number"
                min="1"
                value={minScore}
                onInput={(e) => setMinScore(Number(e.target.value))}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div class="mt-4">
              <label htmlFor="skillMarkdownInput" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Skill Markdown
              </label>
              <textarea
                id="skillMarkdownInput"
                rows="10"
                value={formData.content}
                onInput={(e) => handleInputChange('content', e.target.value)}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="# Billing

keywords: invoice,payment

Guidelines..."
              ></textarea>
            </div>

            <div class="mt-6 flex flex-wrap gap-2">
              <button
                onClick={handleSaveSkill}
                class="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Save Skill
              </button>
              <button
                onClick={handleDeleteSkill}
                class="inline-flex items-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Delete Skill
              </button>
              <button
                onClick={handleSaveSettings}
                class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
              >
                Save Skill Settings
              </button>
            </div>

            <p class="mt-4 text-xs text-gray-500 dark:text-gray-400">
              Skills are applied only on query match, or when explicitly referenced as{' '}
              <code class="rounded bg-gray-100 px-1 py-0.5 text-xs font-mono dark:bg-gray-700">
                $skill_id
              </code>.
            </p>
            <div id="statusLine" class="mt-4 text-sm status-line"></div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default SkillsPage