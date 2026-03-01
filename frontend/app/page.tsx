'use client'
import { useState, useRef } from 'react'

type Stage = 'three-videos' | 'fading-out' | 'single-video' | 'flashing' | 'image'

export default function Home() {
  const [stage, setStage] = useState<Stage>('three-videos')
  const [flash, setFlash] = useState(false)
  const finishedCount = useRef(0)

  const [counts, setCounts] = useState({ arm: 0, hip: 0, knee: 0 })

// Trigger counting when stage becomes 'image'
const startCounting = (key: 'arm' | 'hip' | 'knee', delay: number) => {
  setTimeout(() => {
    let n = 0
    const interval = setInterval(() => {
      n += 2
      if (n >= 99) {
        n = 99
        clearInterval(interval)
      }
      setCounts(prev => ({ ...prev, [key]: n }))
    }, 20)
  }, delay)
}

  const handleShortEnded = () => {
    if (finishedCount.current === 0) {
      document.querySelectorAll('.short-video').forEach((v) => {
        (v as HTMLVideoElement).pause()
      })
    }
    finishedCount.current += 1
    if (finishedCount.current === 1) {
      setStage('fading-out')
      setTimeout(() => setStage('single-video'), 1000)
    }
  }

  const handleSingleVideoEnded = () => {
    setStage('flashing')
    setFlash(true)
    setTimeout(() => {
      setFlash(false)
      setStage('image')
      startCounting('arm',  900)   // matches stat-1 animation delay
      startCounting('hip',  1300)  // matches stat-2
      startCounting('knee', 1700)  // matches stat-3
    }, 600)
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap');

        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes fadeOut {
          from { opacity: 1; }
          to   { opacity: 0; }
        }

        /* Vertic slides in from left with motion blur */
        @keyframes slideInLeft {
          0%   { opacity: 0; transform: translateX(-120px); filter: blur(18px); }
          60%  { filter: blur(4px); }
          100% { opacity: 1; transform: translateX(0);    filter: blur(0px); }
        }

        /* AI slides in from right with motion blur */
        @keyframes slideInRight {
          0%   { opacity: 0; transform: translateX(120px); filter: blur(18px); }
          60%  { filter: blur(4px); }
          100% { opacity: 1; transform: translateX(0);    filter: blur(0px); }
        }

        /* Each stat fades down from above with blur */
        @keyframes fadeInDown {
          0%   { opacity: 0; transform: translateY(-24px); filter: blur(10px); }
          100% { opacity: 1; transform: translateY(0);     filter: blur(0px); }
        }

        /* Flash pulse */
        @keyframes flashPulse {
          0%   { opacity: 0; }
          30%  { opacity: 1; }
          100% { opacity: 0; }
        }

        .vertic-text {
          font-family: 'Bebas Neue', sans-serif;
          animation: slideInLeft 0.9s cubic-bezier(0.22, 1, 0.36, 1) forwards;
          opacity: 0;
        }
        .ai-text {
          font-family: 'Bebas Neue', sans-serif;
          animation: slideInRight 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.15s forwards;
          opacity: 0;
        }
        .stat-1 {
          animation: fadeInDown 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.9s forwards;
          opacity: 0;
        }
        .stat-2 {
          animation: fadeInDown 0.7s cubic-bezier(0.22, 1, 0.36, 1) 1.3s forwards;
          opacity: 0;
        }
        .stat-3 {
          animation: fadeInDown 0.7s cubic-bezier(0.22, 1, 0.36, 1) 1.7s forwards;
          opacity: 0;
        }
        .image-wrap {
          animation: fadeIn 0.6s ease forwards;
        }
        .flash-overlay {
          animation: flashPulse 0.6s ease forwards;
        }
        .start-btn {
          font-family: 'Inter', sans-serif;
          background: rgba(255,255,255,0.15);
          backdrop-filter: blur(8px);
          border: 1.5px solid rgba(255,255,255,0.6);
          color: white;
          padding: 12px 28px;
          border-radius: 999px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.3s ease, border-color 0.3s ease;
          letter-spacing: 0.03em;
        }
        .start-btn:hover {
          background: transparent;
          border-color: rgba(255,255,255,0.3);
        }

        /* Connector lines */
        .connector {
          position: absolute;
          background: white;
        }

        .stat-label {
          font-family: 'Inter', sans-serif;
          font-weight: 700;
          font-size: 1.4vw;
          color: white;
          text-shadow: 0 2px 16px rgba(0,0,0,0.8), 0 0px 40px rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          gap: 8px;
          white-space: nowrap;
        }
        .stat-number {
          font-family: 'Bebas Neue', sans-serif;
          font-size: 1.8vw;
          color: #39ff14;
          text-shadow: 0 0 12px rgba(57,255,20,0.6);
        }
        .dot {
          width: 10px;
          height: 10px;
          background: white;
          border-radius: 50%;
          flex-shrink: 0;
          box-shadow: 0 0 8px rgba(255,255,255,0.8);
        }
      `}</style>

      <main style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: 'black' }}>

        {/* ── 3 shorts side by side ── */}
        {(stage === 'three-videos' || stage === 'fading-out') && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex',
            opacity: stage === 'fading-out' ? 0 : 1,
            transition: 'opacity 1s ease'
          }}>
            {['/videos/LebronJames Dunk.mp4', '/videos/MJ Dunk.mp4', '/videos/Westbrook DUNK 1.mp4'].map((src, i) => (
              <div key={i} style={{ flex: 1, position: 'relative' }}>
                <video
                  autoPlay muted playsInline
                  onEnded={handleShortEnded}
                  className="short-video"
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
                >
                  <source src={src} type="video/mp4" />
                </video>
              </div>
            ))}
          </div>
        )}

        {/* ── Single video ── */}
        {stage === 'single-video' && (
          <video
            autoPlay muted playsInline
            onEnded={handleSingleVideoEnded}
            style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', objectFit: 'contain', animation: 'fadeIn 0.8s ease forwards' }}
          >
            <source src="/videos/Vince carter2.mp4" type="video/mp4" />
          </video>
        )}

        {/* ── Flash ── */}
        {flash && (
          <div className="flash-overlay" style={{ position: 'absolute', inset: 0, background: 'white', zIndex: 50 }} />
        )}

        {/* ── Landing image ── */}
        {stage === 'image' && (
          <div className="image-wrap" style={{ position: 'absolute', inset: 0 }}>

            {/* Background image */}
            <img
              src="/Images/VinceCarter.jpg"
              alt="Vince Carter"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />

            {/* Dark overlay for contrast */}
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.18)' }} />

            {/* ── Start Jumping button top right ── */}
            <div style={{ position: 'absolute', top: '3vh', right: '2.5vw', zIndex: 10 }}>
              <button className="start-btn" onClick={() => alert('Navigate to upload page')}>
                Start Jumping
              </button>
            </div>

            {/* ── VERTIC — slides in from left, left of Vince's head ── */}
            <div className="vertic-text" style={{
              position: 'absolute',
              top: '17vh',
              left: '27vw',
              fontSize: '9vw',
              color: 'white',
              lineHeight: 1,
              textShadow: '0 4px 40px rgba(0,0,0,0.7)',
            }}>
              Vertic
            </div>

            {/* ── AI — slides in from right, right of Vince's head ── */}
            <div className="ai-text" style={{
              position: 'absolute',
              top: '19vh',
              left: '60vw',
              fontSize: '20vw',
              color: 'white',
              lineHeight: 1,
              textShadow: '0 4px 40px rgba(0,0,0,0.7)',
            }}>
              AI
            </div>

            {/* ── Stat 1: Arm Swing (top, left side) ── */}
            <div className="stat-1" style={{ position: 'absolute', top: '36.5vh', left: '30vw' }}>
              <div className="stat-label">
              <span className="stat-number">{counts.arm}</span>
                Arm Swing
                <div className="dot" />
              </div>
              {/* Horizontal connector line */}
              <div style={{
                position: 'absolute', top: '50%', left: '100%',
                width: '6vw', height: '2px', background: 'white',
                boxShadow: '0 0 6px rgba(255,255,255,0.5)'
              }} />
            </div>

            {/* ── Stat 2: Hip Flexion (middle, left side) ── */}
            <div className="stat-2" style={{ position: 'absolute', top: '53vh', left: '31vw' }}>
              <div className="stat-label">
              <span className="stat-number">{counts.hip}</span>
                Hip Flexion
                <div className="dot" />
              </div>
              <div style={{
                position: 'absolute', top: '50%', left: '100%',
                width: '6vw', height: '2px', background: 'white',
                boxShadow: '0 0 6px rgba(255,255,255,0.5)'
              }} />
            </div>

            {/* ── Stat 3: Knee Flexion (middle, right side) ── */}
            <div className="stat-3" style={{ position: 'absolute', top: '54vh', right: '28vw' }}>
              <div className="stat-label">
                <div className="dot" />
                <span className="stat-number">{counts.knee}</span>
                Knee Flexion
              </div>
              <div style={{
                position: 'absolute', top: '50%', right: '100%',
                width: '6vw', height: '2px', background: 'white',
                boxShadow: '0 0 6px rgba(255,255,255,0.5)'
              }} />
            </div>

            {/* ── Bottom chevron ── */}
            <div style={{
              position: 'absolute', bottom: '3vh', left: '50%',
              transform: 'translateX(-50%)',
              color: 'white', fontSize: '2vw', opacity: 0.7
            }}>
              &#8964;
            </div>

          </div>
        )}

      </main>
    </>
  )
}