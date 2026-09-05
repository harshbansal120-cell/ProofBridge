import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Landing } from './pages/Landing'
import { NewVerification } from './pages/NewVerification'
import { Dashboard } from './pages/Dashboard'
import { ProcessorView } from './pages/ProcessorView'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="new" element={<NewVerification />} />
        <Route path="dash" element={<Dashboard />} />
        <Route path="processor/:requestId" element={<ProcessorView />} />
      </Route>
    </Routes>
  )
}

export default App
