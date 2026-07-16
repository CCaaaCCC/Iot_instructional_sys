import { ref, watch } from 'vue'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'greenhouse-theme'

const currentTheme = ref<Theme>(loadTheme())

function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {}
  return 'dark'
}

function applyTheme(theme: Theme) {
  const html = document.documentElement
  if (theme === 'light') {
    html.setAttribute('data-theme', 'light')
  } else {
    html.removeAttribute('data-theme')
  }
}

function enableTransition() {
  document.documentElement.classList.add('theme-transition')
}

function disableTransition() {
  document.documentElement.classList.remove('theme-transition')
}

if (typeof document !== 'undefined') {
  applyTheme(currentTheme.value)
}

watch(currentTheme, (newTheme) => {
  enableTransition()
  applyTheme(newTheme)
  try {
    localStorage.setItem(STORAGE_KEY, newTheme)
  } catch {}
  setTimeout(disableTransition, 400)
})

export function useTheme() {
  function toggle() {
    currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(theme: Theme) {
    currentTheme.value = theme
  }

  return {
    theme: currentTheme,
    toggle,
    setTheme,
  }
}
