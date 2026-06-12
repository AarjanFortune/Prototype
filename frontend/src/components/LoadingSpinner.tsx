import './LoadingSpinner.css'

interface LoadingSpinnerProps {
  message?: string
}

export default function LoadingSpinner({ message = 'Processing...' }: LoadingSpinnerProps) {
  return (
    <div className="loading-container">
      <div className="spinner">
        <div className="spinner-ring"></div>
      </div>
      <p>{message}</p>
    </div>
  )
}
