import { useEffect, useRef, useState } from 'react'

const MAX_SECONDS = 20
const TARGET_RATE = 16_000

export interface VoiceSample {
  wavBase64: string
  durationSeconds: number
}

function encodeWav(chunks: Float32Array[], sourceRate: number): VoiceSample {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const source = new Float32Array(length)
  let cursor = 0
  for (const chunk of chunks) { source.set(chunk, cursor); cursor += chunk.length }
  const durationSeconds = source.length / sourceRate
  const outputLength = Math.max(1, Math.round(durationSeconds * TARGET_RATE))
  const output = new Float32Array(outputLength)
  const ratio = sourceRate / TARGET_RATE
  for (let index = 0; index < outputLength; index += 1) {
    const position = index * ratio
    const left = Math.min(source.length - 1, Math.floor(position))
    const right = Math.min(source.length - 1, left + 1)
    const fraction = position - left
    output[index] = source[left] * (1 - fraction) + source[right] * fraction
  }
  const buffer = new ArrayBuffer(44 + output.length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => [...value].forEach((character, index) => view.setUint8(offset + index, character.charCodeAt(0)))
  text(0, 'RIFF'); view.setUint32(4, 36 + output.length * 2, true); text(8, 'WAVE')
  text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, TARGET_RATE, true); view.setUint32(28, TARGET_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  text(36, 'data'); view.setUint32(40, output.length * 2, true)
  output.forEach((sample, index) => view.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample)) * (sample < 0 ? 32768 : 32767), true))
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000))
  return { wavBase64: btoa(binary), durationSeconds }
}

export function VoiceCapture({ enabled, disabled, sample, onChange }: { enabled: boolean; disabled: boolean; sample: VoiceSample | null; onChange: (sample: VoiceSample | null) => void }) {
  const [status, setStatus] = useState<'idle'|'recording'|'ready'|'error'>('idle')
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState('')
  const resources = useRef<{stream: MediaStream; context: AudioContext; processor: ScriptProcessorNode; source: MediaStreamAudioSourceNode; chunks: Float32Array[]; started: number} | null>(null)
  const timer = useRef<number | null>(null)

  function cleanup() {
    if (timer.current !== null) window.clearInterval(timer.current)
    timer.current = null
    const active = resources.current
    if (!active) return
    active.processor.disconnect(); active.source.disconnect(); active.stream.getTracks().forEach(track => track.stop())
    void active.context.close(); resources.current = null
  }

  function stop(keep = true) {
    const active = resources.current
    if (!active) return
    if (keep && active.chunks.length) {
      const sample = encodeWav(active.chunks, active.context.sampleRate)
      onChange(sample); setSeconds(sample.durationSeconds); setStatus('ready')
    } else { onChange(null); setSeconds(0); setStatus('idle') }
    cleanup()
  }

  async function start() {
    onChange(null); setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }, video: false })
      const context = new AudioContext()
      const source = context.createMediaStreamSource(stream)
      const processor = context.createScriptProcessor(4096, 1, 1)
      const chunks: Float32Array[] = []
      processor.onaudioprocess = event => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
      source.connect(processor); processor.connect(context.destination)
      resources.current = { stream, context, processor, source, chunks, started: performance.now() }
      setStatus('recording'); setSeconds(0)
      timer.current = window.setInterval(() => {
        const active = resources.current
        if (!active) return
        const elapsed = (performance.now() - active.started) / 1000
        setSeconds(elapsed)
        if (elapsed >= MAX_SECONDS) stop(true)
      }, 200)
    } catch {
      cleanup(); setStatus('error'); setError('Microphone access was unavailable. You can continue with text only.')
    }
  }

  useEffect(() => () => cleanup(), [])
  const displayStatus = status === 'ready' && !sample ? 'idle' : status
  if (!enabled) return <div className="voice-capture unavailable"><span>Voice analysis unavailable</span><small>The message will use text analysis.</small></div>
  return <div className={`voice-capture ${displayStatus}`}>
    {displayStatus === 'recording' ? <button type="button" onClick={()=>stop(true)} disabled={disabled} aria-label="Stop voice recording">■ Stop</button> : <button type="button" onClick={start} disabled={disabled} aria-label={displayStatus === 'ready' ? 'Replace voice recording' : 'Record voice sample'}>● {displayStatus === 'ready' ? 'Record again' : 'Add voice'}</button>}
    <span aria-live="polite">{displayStatus === 'recording' ? `Recording ${seconds.toFixed(1)} / ${MAX_SECONDS}s` : displayStatus === 'ready' ? `${seconds.toFixed(1)}s voice sample attached` : 'Optional · sent to OpenAI for transcription · not stored'}</span>
    {displayStatus === 'ready' && <button type="button" className="remove-audio" onClick={()=>{onChange(null);setStatus('idle');setSeconds(0)}}>Remove</button>}
    {error && <small role="status">{error}</small>}
  </div>
}
