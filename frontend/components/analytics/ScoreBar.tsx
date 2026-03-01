interface ScoreBarProps {
  score: number
  maxScore: number
  color: string
}

export default function ScoreBar({ score, maxScore, color }: ScoreBarProps) {
  const percentage = (score / maxScore) * 100

  return (
    <div className="w-full h-2 rounded-full bg-score-bar overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700 ease-out"
        style={{ width: `${percentage}%`, backgroundColor: color }}
      />
    </div>
  )
}
