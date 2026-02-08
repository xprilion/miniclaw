import { render } from 'preact'
import { Router } from 'preact-router'
import { useMemo, useState, useEffect, useContext } from 'preact/hooks'
import { createContext } from 'preact'

import './styles/globals.css'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import ChatPage from './pages/ChatPage'
import SetupPage from './pages/SetupPage'
import EnhancedSetupPage from './pages/EnhancedSetupPage'
import SimplifiedSetupPage from './pages/SimplifiedSetupPage'
import SkillsPage from './pages/SkillsPage'
import SchedulerPage from './pages/SchedulerPage'
import MonitoringPage from './pages/MonitoringPage'

// Create context for global state
export const AppContext = createContext()

// Create a custom hook for easier theme access
export const useTheme = () => {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useTheme must be used within an AppProvider')
  }
  return context
}

export function App() {
  const [theme, setTheme] = useState(() => {
    try {
      const savedTheme = localStorage.getItem('miniclaw_theme')
      if (savedTheme) return savedTheme
      
      // Check system preference if no saved theme
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark'
      }
      return 'light'
    } catch {
      return 'light'
    }
  })

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    try {
      localStorage.setItem('miniclaw_theme', newTheme)
      // Add transition class for smooth theme switching
      document.documentElement.classList.add('theme-transition')
      // Force a reflow to ensure the transition class is applied
      document.documentElement.offsetHeight
      if (newTheme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      // Remove transition class after animation completes
      setTimeout(() => {
        document.documentElement.classList.remove('theme-transition')
      }, 300)
    } catch (error) {
      console.error('Error setting theme:', error)
    }
  }

  // Apply theme on initial load
  useEffect(() => {
    try {
      // Remove any existing theme classes to prevent conflicts
      document.documentElement.classList.remove('dark', 'theme-transition')
      
      if (theme === 'dark') {
        document.documentElement.classList.add('dark')
      }
      // For light theme, we just ensure 'dark' class is removed (already done above)
    } catch (error) {
      console.error('Error applying theme:', error)
    }
  }, [theme])

  // Listen for system theme changes when using 'system' preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e) => {
      // Only update if user hasn't explicitly chosen a theme
      try {
        const savedTheme = localStorage.getItem('miniclaw_theme')
        if (!savedTheme) {
          const newTheme = e.matches ? 'dark' : 'light'
          setTheme(newTheme)
        }
      } catch (error) {
        console.error('Error handling system theme change:', error)
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const contextValue = useMemo(() => ({
    theme,
    toggleTheme
  }), [theme])

  return (
    <AppContext.Provider value={contextValue}>
      <div class="min-h-full bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <Router>
          <LandingPage path="/" />
          <ChatPage path="/chat" />
          <SetupPage path="/setup/legacy" />
          <EnhancedSetupPage path="/setup/enhanced" />
          <SimplifiedSetupPage path="/setup" />
          <SkillsPage path="/skills" />
          <SchedulerPage path="/scheduler" />
          <MonitoringPage path="/monitoring" />
        </Router>
      </div>
    </AppContext.Provider>
  )
}

render(<App />, document.getElementById('app'))