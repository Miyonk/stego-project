import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ThreeCarrier from './ThreeCarrier.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <ThreeCarrier />
  </StrictMode>,
)
