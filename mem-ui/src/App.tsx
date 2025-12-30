import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Timeline from './pages/Timeline'
import Settings from './pages/Settings'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <Toaster position="top-right" toastOptions={{
        duration: 4000,
        style: { background: '#333', color: '#fff' }
      }} />
      <Routes>
        <Route path="/" element={<Timeline />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
