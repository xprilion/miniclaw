import { useContext } from 'preact/hooks'
import { AppContext } from '../main'
import { route } from 'preact-router'

const Navbar = () => {
  const { theme, toggleTheme } = useContext(AppContext)
  
  return (
    <header class="bg-white shadow dark:bg-gray-800">
      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between">
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold leading-tight text-primary-600 dark:text-primary-400">MiniClaw</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Personal AI Assistant</p>
          </div>
          <nav class="mt-4 md:mt-0 flex flex-wrap gap-2">
            <a href="/" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Overview</a>
            <a href="/chat" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Chat</a>
            <div class="relative group inline-flex items-center">
              <a href="/setup" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Setup</a>
              <div class="absolute right-0 mt-1 w-48 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 hidden group-hover:block z-50">
                <div class="py-1">
                  <a href="/setup" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-600">Basic Setup</a>
                  <a href="/setup/enhanced" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-600">Enhanced Setup</a>
                </div>
              </div>
            </div>
            <a href="/skills" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Skills</a>
            <a href="/jobs" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Jobs</a>
            <a href="/monitoring" class="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Monitoring</a>
            <button 
              onClick={toggleTheme}
              type="button"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              class="inline-flex items-center justify-center rounded-md bg-white p-2 text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-all duration-300 ease-in-out hover:scale-105"
            >
              {theme === 'dark' ? (
                <svg class="h-5 w-5 text-yellow-400 transition-colors duration-300" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd" />
                </svg>
              ) : (
                <svg class="h-5 w-5 text-gray-700 dark:text-gray-300 transition-colors duration-300" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Navbar