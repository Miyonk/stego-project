import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import PhotoStego from './PhotoStego.jsx'
import ThreeCarrier from './ThreeCarrier.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <PhotoStego />
    <ThreeCarrier />
  </StrictMode>,
)
