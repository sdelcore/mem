import { Routes, Route } from 'react-router-dom'
import Timeline from './pages/Timeline'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Timeline />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  )
}

export default App
