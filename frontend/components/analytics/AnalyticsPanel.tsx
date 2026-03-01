import { useState } from 'react'
import ScoreBar from './ScoreBar'

export interface JumpAnalysisData {
  total_score: number
  jump_height: number
  hip_flexion_score: number
  hip_flexion_angle: number
  knee_flexion_score: number
  knee_flexion_angle: number
  swing_velocity_score: number
  swing_velocity: number
  overall_feedback: string
  annotated_video_url: string
}

interface AnalyticsPanelProps {
  data: JumpAnalysisData | null
}

const SUBTABS = [
  { key: 'hip', label: 'Hip Flexion' },
  { key: 'knee', label: 'Knee Flexion' },
  { key: 'arm', label: 'Arm Swing' },
] as const

type SubtabKey = (typeof SUBTABS)[number]['key']

const IDEAL_VALUES = {
  hip: { angle: 120, unit: '°', research: 'https://pubmed.ncbi.nlm.nih.gov/25264539/' },
  knee: { angle: 90, unit: '°', research: 'https://pubmed.ncbi.nlm.nih.gov/25264539/' },
  arm: { angle: 180, unit: '°/s', research: 'https://pubmed.ncbi.nlm.nih.gov/25264539/' },
}

function getScoreColor(score: number): string {
  if (score >= 8) return 'hsl(160, 82%, 39%)'
  if (score >= 5) return 'hsl(45, 93%, 55%)'
  return 'hsl(0, 84%, 60%)'
}

function getScoreLabel(score: number): string {
  if (score >= 8) return 'EXCELLENT'
  if (score >= 5) return 'GOOD'
  return 'NEEDS WORK'
}

function getScoreLabelClass(score: number): string {
  if (score >= 8) return 'text-primary'
  if (score >= 5) return 'text-score-good'
  return 'text-score-needs-work'
}

export default function AnalyticsPanel({ data }: AnalyticsPanelProps) {
  const [activeTab, setActiveTab] = useState<SubtabKey | null>(null)

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p className="text-sm">Upload a video to see your jump analysis</p>
      </div>
    )
  }

  const subtabData = {
    hip: { score: data.hip_flexion_score, value: data.hip_flexion_angle },
    knee: { score: data.knee_flexion_score, value: data.knee_flexion_angle },
    arm: { score: data.swing_velocity_score, value: data.swing_velocity },
  }

  const toggleTab = (key: SubtabKey) => {
    setActiveTab(activeTab === key ? null : key)
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="mb-4">
        <div className="flex items-baseline gap-3 mb-1">
          <h2 className="text-lg font-semibold text-foreground">Jump Score</h2>
          <span className="text-3xl font-bold text-foreground">{data.total_score}</span>
          <span className="text-lg text-muted-foreground">/ 100</span>
        </div>
        <div className="w-full h-3 rounded-full bg-score-bar overflow-hidden relative">
          <div
            className="h-full rounded-full bg-primary transition-all duration-1000 ease-out"
            style={{ width: `${data.total_score}%` }}
          />
          <div className="absolute top-0 right-[5%] h-full w-0.5 bg-foreground/40" />
        </div>
        <div className="flex justify-between mt-1">
          <span className={`text-xs font-semibold ${getScoreLabelClass(data.total_score / 10)}`}>
            Your score
          </span>
          <span className="text-xs font-medium text-muted-foreground">Target (95+)</span>
        </div>
      </div>

      <div className="mb-3 p-3 rounded-xl bg-surface-elevated border border-border">
        <p className="text-sm text-muted-foreground mb-1">Jump Height</p>
        <p className="text-2xl font-bold text-foreground">
          {data.jump_height} <span className="text-sm font-normal text-muted-foreground">cm</span>
        </p>
      </div>

      <div className="mb-3 p-3 rounded-xl bg-surface-elevated border border-border">
        <p className="text-sm font-medium text-muted-foreground mb-2">Overall Feedback</p>
        <p className="text-sm text-foreground leading-relaxed">{data.overall_feedback}</p>
      </div>

      <div className="mb-4">
        <h3 className="text-sm font-semibold text-foreground mb-2">Component Scores</h3>
        <div className="flex gap-2">
          {SUBTABS.map((tab) => {
            const score = subtabData[tab.key].score
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => toggleTab(tab.key)}
                className={`flex-1 rounded-xl border px-3 py-2 transition-all duration-200 text-left ${
                  isActive
                    ? 'border-primary bg-primary/[0.05]'
                    : 'border-border hover:border-primary/30'
                }`}
              >
                <p className="text-xs font-medium text-muted-foreground mb-1">{tab.label}</p>
                <ScoreBar score={score} maxScore={10} color={getScoreColor(score)} />
                <div className="flex items-baseline justify-between mt-1.5">
                  <span className="text-sm font-bold text-foreground">{score} / 10</span>
                  <span className={`text-[10px] font-bold ${getScoreLabelClass(score)}`}>
                    {getScoreLabel(score)}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {activeTab && (
        <div className="p-3 rounded-xl border border-primary/20 bg-primary/[0.02] animate-fadeIn">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                Your {activeTab === 'arm' ? 'angular velocity' : 'angle'}
              </span>
              <span className="text-lg font-bold text-foreground">
                {subtabData[activeTab].value}
                {IDEAL_VALUES[activeTab].unit}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                Ideal {activeTab === 'arm' ? 'angular velocity' : 'angle'}
              </span>
              <span className="text-lg font-bold text-primary">
                {IDEAL_VALUES[activeTab].angle}
                {IDEAL_VALUES[activeTab].unit}
              </span>
            </div>
            <a
              href={IDEAL_VALUES[activeTab].research}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline mt-1"
            >
              <span aria-hidden="true">↗</span>
              View research paper
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
