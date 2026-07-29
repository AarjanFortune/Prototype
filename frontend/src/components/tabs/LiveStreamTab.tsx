import React, { useState, useEffect, useRef } from 'react'

export default function LiveStreamTab() {
  const [isRecording, setIsRecording] = useState(false)
  const [statusText, setStatusText] = useState('Ready to connect')
  const [activeNotes, setActiveNotes] = useState<{ stringIdx: number, fret: number }[]>([])
  
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)

  const stringLabels = ['e', 'B', 'G', 'D', 'A', 'E']

  const startStreaming = async () => {
    try {
      console.log('[GUITARICA LIVE] Requesting Microphone Access...')
      setStatusText('Requesting microphone access...')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const clientId = `web-client-${Date.now()}`
      console.log(`[GUITARICA LIVE] Establishing WebSocket to ws://localhost:8000/ws/stream/${clientId}`)
      
      const ws = new WebSocket(`ws://localhost:8000/ws/stream/${clientId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[GUITARICA LIVE] WebSocket Connected. Initializing Audio Context.')
        setStatusText('Connected. Listening for guitar...')
        setIsRecording(true)

        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 44100 })
        audioContextRef.current = audioContext

        const source = audioContext.createMediaStreamSource(stream)
        const processor = audioContext.createScriptProcessor(4096, 1, 1)
        processorRef.current = processor

        let chunkCount = 0

        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0)
          
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'audio_chunk',
              data: Array.from(inputData),
              tempo: 120.0
            }))
            
            chunkCount++
            if (chunkCount % 50 === 0) {
              console.log(`[GUITARICA LIVE] Sent 50 audio chunks to backend...`)
            }
          }
        }

        source.connect(processor)
        processor.connect(audioContext.destination)
      }

      ws.onmessage = (event) => {
        const response = JSON.parse(event.data)
        
        if (response.type === 'transcription' && response.tab && response.tab.length > 0) {
          const latestFrame = response.tab[response.tab.length - 1]
          const currentNotes: { stringIdx: number, fret: number }[] = []

          let hasNotes = false
          latestFrame.forEach((fretValue: number, stringIdx: number) => {
            if (fretValue >= 0 && fretValue < 30) {
              const mappedStringIdx = 5 - stringIdx 
              currentNotes.push({ stringIdx: mappedStringIdx, fret: fretValue })
              hasNotes = true
            }
          })

          if (hasNotes) {
             console.log('[GUITARICA LIVE] Detected Notes:', currentNotes)
          }

          setActiveNotes(currentNotes)
        }
      }

      ws.onerror = (error) => {
        console.error('[GUITARICA LIVE] WebSocket Error:', error)
        setStatusText('WebSocket Connection Error')
        stopStreaming()
      }

      ws.onclose = () => {
        console.log('[GUITARICA LIVE] WebSocket Closed.')
        setStatusText('Connection closed')
        stopStreaming()
      }

    } catch (error) {
      console.error('[GUITARICA LIVE] Initialization Error:', error)
      setStatusText('Microphone access denied or unavailable')
      setIsRecording(false)
    }
  }

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

    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    setStatusText('Session ended')
    console.log('[GUITARICA LIVE] Session Terminated Cleanly.')
  }

  useEffect(() => {
    return () => {
      stopStreaming()
    }
  }, [])

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '32px', maxWidth: '520px' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem', fontWeight: 400, marginBottom: '6px', color: 'var(--color-ink)' }}>
            Live Studio Input
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', lineHeight: '1.4' }}>
            Stream audio directly from your microphone to the neural network for real-time inference.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button 
          onClick={isRecording ? stopStreaming : startStreaming}
          style={{
            alignSelf: 'flex-start',
            background: 'none',
            border: 'none',
            borderBottom: '2px solid',
            borderBottomColor: isRecording ? '#c94b4b' : 'var(--color-ink)',
            color: isRecording ? '#c94b4b' : 'var(--color-ink)',
            fontSize: '0.72rem',
            fontWeight: 600,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            paddingBottom: '2px',
            transition: 'color 0.2s, border-color 0.2s'
          }}
        >
          {isRecording ? '[ Stop Recording ]' : '[ Initialize Mic ]'}
        </button>
        <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Status: {statusText}
        </span>
      </div>

      <div style={{
        display: 'flex', flexDirection: 'column', gap: '16px', background: 'transparent',
        border: '1px solid var(--color-border)', borderRadius: '4px', padding: '24px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Real-Time Fretboard Matrix
          </span>
          <span style={{ fontSize: '0.62rem', color: isRecording ? '#c94b4b' : 'var(--color-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            {isRecording ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        <div style={{ position: 'relative', width: '100%', height: '140px', background: '#fcfcfd', border: '1px solid #e5e5ea', borderRadius: '4px' }}>
          
          {stringLabels.map((label, idx) => (
            <div key={`string-label-${idx}`} style={{
              position: 'absolute', left: '-16px', top: `${(idx * 24) + 10}px`,
              fontSize: '10px', fontWeight: 600, color: 'var(--color-muted)'
            }}>
              {label}
            </div>
          ))}

          {Array.from({ length: 22 }).map((_, i) => (
            <div key={`fret-${i}`} style={{ position: 'absolute', left: `${(i / 21) * 100}%`, top: 0, bottom: 0, width: '1px', background: '#d1d1d6' }} />
          ))}

          {Array.from({ length: 6 }).map((_, i) => (
            <div key={`string-line-${i}`} style={{ position: 'absolute', left: 0, right: 0, top: `${(i * 24) + 14}px`, height: '1px', background: '#e5e5ea' }} />
          ))}
          
          {activeNotes.map((note, i) => {
            const fretPos = (note.fret / 21) * 100
            const stringPos = (note.stringIdx * 24) + 14

            return (
              <div 
                key={`live-fret-${i}`}
                style={{
                  position: 'absolute', left: `${fretPos}%`, top: `${stringPos}px`, width: '14px', height: '14px',
                  borderRadius: '50%', background: '#c94b4b', transform: 'translate(-50%, -50%)', 
                  boxShadow: '0 0 10px rgba(201, 75, 75, 0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
              >
                <span style={{ color: '#fff', fontSize: '8px', fontWeight: 700 }}>{note.fret}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}