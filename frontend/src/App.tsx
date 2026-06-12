import './App.css'
import { useState } from 'react'
import Header from './components/Header'
import Navigation from './components/Navigation'
import UploadTab from './components/tabs/UploadTab'
import YouTubeTab from './components/tabs/YouTubeTab'
import LiveStreamTab from './components/tabs/LiveStreamTab'

type TabType = 'upload' | 'youtube' | 'live'

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('upload')

  return (
    <div className="app">
      <Header />
      <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="main-content">
        {activeTab === 'upload' && <UploadTab />}
        {activeTab === 'youtube' && <YouTubeTab />}
        {activeTab === 'live' && <LiveStreamTab />}
      </main>
    </div>
  )
}

export default App
