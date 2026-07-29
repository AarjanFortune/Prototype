import { useEffect, useRef, useState } from 'react'

interface ActiveNote {
  stringIdx: number
  fret: number
}

const STRING_LABELS = ['e', 'B', 'G', 'D', 'A', 'E']

export default function LiveInputPanel() {
  const [isRecording, setIsRecording] = useState(false)
  const [statusText, setStatusText] = useState('Ready')
  const [activeNotes, setActiveNotes] = useState<ActiveNote[]>([])

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)

  const stopStreaming = () => {
    setIsRecording(false)
    setActiveNotes([])

    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'finish' }))
      }
      wsRef.current.close()
      wsRef.current = null
    }

    processorRef.current?.disconnect()
    processorRef.current = null

    audioContextRef.current?.close()
    audioContextRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setStatusText('Session ended')
  }

  const startStreaming = async () => {
    try {
      setStatusText('Requesting microphone access')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const clientId = `web-client-${Date.now()}`
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws/stream/${clientId}`)
      wsRef.current = ws

      ws.onopen = () => {
        setStatusText('Listening')
        setIsRecording(true)

        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
        const audioContext = new AudioContextClass({ sampleRate: 44100 })
        audioContextRef.current = audioContext

        const source = audioContext.createMediaStreamSource(stream)
        const processor = audioContext.createScriptProcessor(4096, 1, 1)
        processorRef.current = processor

        processor.onaudioprocess = (event) => {
          const inputData = event.inputBuffer.getChannelData(0)
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'audio_chunk',
              data: Array.from(inputData),
              tempo: 120,
            }))
          }
        }

        source.connect(processor)
        processor.connect(audioContext.destination)
      }

      ws.onmessage = (event) => {
        const response = JSON.parse(event.data)
        if (response.type !== 'transcription' || !Array.isArray(response.tab) || response.tab.length === 0) {
          return
        }

        const latestFrame = response.tab[response.tab.length - 1]
        const notes = latestFrame
          .map((fret: number, stringIdx: number) => ({ fret, stringIdx: 5 - stringIdx }))
          .filter((note: ActiveNote) => note.fret >= 0 && note.fret < 30)

        setActiveNotes(notes)
      }

      ws.onerror = () => {
        setStatusText('Connection error')
        stopStreaming()
      }

      ws.onclose = () => {
        if (isRecording) stopStreaming()
      }
    } catch {
      setStatusText('Microphone unavailable')
      setIsRecording(false)
    }
  }

  useEffect(() => stopStreaming, [])

  return (
    <section className="input-section live-section" aria-labelledby="live-title">
      <div className="section-heading">
        <span>Live input</span>
        <h1 id="live-title">Play</h1>
      </div>

      <div className="live-controls">
        <button
          type="button"
          className="primary-action"
          onClick={isRecording ? stopStreaming : startStreaming}
        >
          {isRecording ? 'Stop listening' : 'Start listening'}
        </button>
        <span className="live-status">{statusText}</span>
      </div>

      <div className="fretboard" aria-label="Live fretboard">
        {STRING_LABELS.map((label, stringIdx) => (
          <div className="fretboard-string" key={label}>
            <span>{label}</span>
            <div className="fretboard-line">
              {Array.from({ length: 12 }).map((_, fretIdx) => (
                <i key={fretIdx} />
              ))}
              {activeNotes
                .filter((note) => note.stringIdx === stringIdx)
                .map((note, noteIdx) => (
                  <b
                    key={`${stringIdx}-${note.fret}-${noteIdx}`}
                    style={{ left: `${Math.min(note.fret, 12) / 12 * 100}%` }}
                  >
                    {note.fret}
                  </b>
                ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
