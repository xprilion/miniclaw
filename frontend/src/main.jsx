import { render } from 'preact'
import { Router } from 'preact-router'
import { useMemo, useState } from 'preact/hooks'
import { createContext } from 'preact'

import './styles/globals.css'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import ChatPage from './pages/ChatPage'
import SetupPage from './pages/SetupPage'
import SkillsPage from './pages/SkillsPage'
import SchedulerPage from './pages/SchedulerPage'
import MonitoringPage from './pages/MonitoringPage'

// Create context for global state
export const AppContext = createContext()

export function App() {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('miniclaw_theme') || 'light'
    } catch {
      return 'light'
    }
  })

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    try {
      localStorage.setItem('miniclaw_theme', newTheme)
      if (newTheme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    } catch (error) {
      console.error('Error setting theme:', error)
    }
  }

  const contextValue = useMemo(() => ({
    theme,
    toggleTheme
  }), [theme])

  return (
    <AppContext.Provider value={contextValue}>
      <div class="min-h-full">
        <Navbar />
        <Router>
          <LandingPage path="/" />
          <ChatPage path="/chat" />
          <SetupPage path="/setup" />
          <SkillsPage path="/skills" />
          <SchedulerPage path="/scheduler" />
          <MonitoringPage path="/monitoring" />
        </Router>
      </div>
    </AppContext.Provider>
  )
}

render(<App />, document.getElementById('app'))