import { useRef, useState, useEffect } from 'react'
import './LiveStreamTab.css'
import LoadingSpinner from '../LoadingSpinner'

interface TabPrediction {
  tab: number[][]
  confidence: number[][]
  n_frames: number
}

export default function LiveStreamTab() {
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const audioContext = useRef<AudioContext | null>(null)
  const analyser = useRef<AnalyserNode | null>(null)
  const microphone = useRef<MediaStreamAudioSourceNode | null>(null)
  const ws = useRef<WebSocket | null>(null)

  const [isRecording, setIsRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [predictions, setPredictions] = useState<TabPrediction[]>([])
  const [currentTab, setCurrentTab] = useState<string>('')
  const [bpm, setBpm] = useState(120)

  const startRecording = async () => {
    try {
      setError(null)
      setPredictions([])
      setCurrentTab('')

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      // Setup audio context
      audioContext.current = new (window.AudioContext || (window as any).webkitAudioContext)()

      // Setup analyser
      microphone.current = audioContext.current.createMediaStreamSource(stream)
      analyser.current = audioContext.current.createAnalyser()
      analyser.current.fftSize = 2048

      // Use ScriptProcessorNode to capture raw audio samples
      const scriptProcessor = audioContext.current.createScriptProcessor(4096, 1, 1)
      
      scriptProcessor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)
        const audioData = Array.from(inputData)
        
        if (ws.current && ws.current.readyState === WebSocket.OPEN && audioData.length > 0) {
          ws.current.send(JSON.stringify({
            type: 'audio_chunk',
            data: audioData,
            tempo: bpm,
          }))
        }
      }

      microphone.current.connect(analyser.current)
      analyser.current.connect(scriptProcessor)
      scriptProcessor.connect(audioContext.current.destination)

      // Connect WebSocket
      const clientId = `client_${Date.now()}`
      ws.current = new WebSocket(`ws://localhost:8000/ws/stream/${clientId}`)

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setLoading(true)
      }

      ws.current.onmessage = (event) => {
        console.log('WebSocket message received:', event.data)
        const data = JSON.parse(event.data)
        console.log('Parsed data:', data)

        if (data.type === 'transcription') {
          console.log('Processing transcription:', data.tab)
          const pred: TabPrediction = {
            tab: data.tab,
            confidence: data.confidence,
            n_frames: data.n_frames,
          }
          setPredictions(prev => [...prev, pred])

          // Format current tab display
          if (data.tab && data.tab.length > 0) {
            console.log('Formatting tab with', data.tab.length, 'frames')
            const tabLines = ['E|', 'A|', 'D|', 'G|', 'B|', 'e|']
            data.tab.forEach((frets: number[]) => {
              frets.forEach((fret: number, stringIdx: number) => {
                const symbol = fret < 0 ? '-' : fret.toString()
                tabLines[stringIdx] += symbol
              })
            })
            const tabOutput = tabLines.join('\n')
            console.log('Tab output:', tabOutput)
            setCurrentTab(tabOutput)
          }
        } else if (data.type === 'done') {
          setIsRecording(false)
          setLoading(false)
        } else if (data.type === 'error') {
          setError(data.error)
          setIsRecording(false)
          setLoading(false)
        }
      }

      ws.current.onerror = () => {
        setError('WebSocket connection failed')
        setIsRecording(false)
      }

      // Start recording
      if (mediaRecorder.current) {
        mediaRecorder.current.start(1000) // Send chunks every second
      }
      setIsRecording(true)

    } catch (err: any) {
      setError(err.message || 'Failed to access microphone')
    }
  }

  const stopRecording = () => {
    if (isRecording) {
      // Stop capturing audio
      if (microphone.current) {
        microphone.current.disconnect()
      }
      
      // Stop all tracks from the stream
      if (microphone.current && (microphone.current as any).mediaStream) {
        (microphone.current as any).mediaStream.getTracks().forEach((track: MediaStreamTrack) => track.stop())
      }
      
      setIsRecording(false)

      // Signal completion to server
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type: 'finish',
          tempo: bpm,
        }))
      }

      // Close audio context
      if (audioContext.current) {
        audioContext.current.close()
      }
    }
  }

  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.close()
      }
      if (isRecording && audioContext.current) {
        audioContext.current.close()
      }
    }
  }, [isRecording])

  return (
    <div className="live-stream-tab">
      <div className="live-container">
        <div className="controls-card">
          <h2>🎙️ Live Recording</h2>
          
          <div className="live-form">
            <div className="form-group">
              <label htmlFor="bpm">Tempo (BPM):</label>
              <input
                id="bpm"
                type="number"
                min="40"
                max="300"
                value={bpm}
                onChange={(e) => setBpm(parseInt(e.target.value))}
                disabled={isRecording}
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="button-group">
              <button
                className="record-button"
                onClick={startRecording}
                disabled={isRecording}
              >
                🔴 Start Recording
              </button>
              <button
                className="stop-button"
                onClick={stopRecording}
                disabled={!isRecording}
              >
                ⏹️ Stop Recording
              </button>
            </div>

            {isRecording && (
              <div className="recording-indicator">
                <span className="pulse"></span>
                <span>Recording in progress...</span>
              </div>
            )}

            <div className="info-box">
              <p><strong>🎸 How it works:</strong></p>
              <ul>
                <li>Click "Start Recording" to begin capturing audio from your microphone</li>
                <li>Play guitar and the app will transcribe in real-time</li>
                <li>Tablature updates as you play</li>
                <li>Click "Stop Recording" when done</li>
              </ul>
            </div>
          </div>
        </div>

        {(loading || isRecording) && <LoadingSpinner message="Processing real-time audio..." />}

        {currentTab && (
          <div className="tab-display-card">
            <h3>📋 Live Tablature</h3>
            <pre className="tab-output">{currentTab}</pre>
          </div>
        )}

        {predictions.length > 0 && (
          <div className="predictions-summary">
            <h3>📊 Transcription Summary</h3>
            <p>Processed {predictions.length} chunks ({predictions.reduce((sum, p) => sum + p.n_frames, 0)} frames total)</p>
            <p>Average confidence: {(
              predictions.reduce((sum, p) => {
                const avg = p.confidence.reduce((s, c) => s + c.reduce((s2, v) => s2 + v, 0), 0) / 
                  (p.confidence.length * p.confidence[0].length)
                return sum + avg
              }, 0) / predictions.length * 100
            ).toFixed(1)}%</p>
          </div>
        )}
      </div>
    </div>
  )
}
