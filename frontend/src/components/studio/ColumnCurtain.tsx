import React, { useEffect, useState } from 'react'
import './ColumnCurtain.css'

interface CurtainProps {
  isActive: boolean
  onAnimationEnd: () => void
}

export default function ColumnCurtain({ isActive, onAnimationEnd }: CurtainProps) {
  const [animating, setAnimating] = useState(false)

  useEffect(() => {
    if (isActive) {
      setAnimating(true)
      const timer = setTimeout(() => {
        onAnimationEnd()
      }, 1250)
      return () => clearTimeout(timer)
    }
  }, [isActive, onAnimationEnd])

  return (
    <div className={`curtain-overlay ${animating ? 'curtain-active' : ''}`}>
      {Array.from({ length: 5 }).map((_, idx) => (
        <div key={idx} className="curtain-column" />
      ))}
    </div>
  )
}