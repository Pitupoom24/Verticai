'use client'

import Link from 'next/link'
import { useState } from 'react'
import VideoUploader from '@/components/analytics/VideoUploader'
import AnalyticsPanel, { type JumpAnalysisData } from '@/components/analytics/AnalyticsPanel'

interface BackendUploadResponse {
  message: string
  output_video: {
    score: number | null
    jump_height: number | null
    hip_normalized_score: number | null
    smallest_loading_min_hip_flexion: number | null
    knee_normalized_score: number | null
    smallest_loading_min_knee_flexion: number | null
    angular_velocity_score: number | null
    angular_velocity: number | null
    llm_report: string | null
    file_path: string | null
    original_filename: string | null
  }
}

const ANALYZE_ENDPOINT = 'http://127.0.0.1:8000/input-videos'

function toPanelData(response: BackendUploadResponse): JumpAnalysisData {
  const output = response.output_video

  // Backend stores jump height in meters; panel displays centimeters.
  const jumpHeightCm = (output.jump_height ?? 0) * 100
  const totalScore = Math.max(0, Math.min(100, output.score ?? 0))

  return {
    total_score: Number(totalScore.toFixed(2)),
    jump_height: Number(jumpHeightCm.toFixed(2)),
    hip_flexion_score: Number((((output.hip_normalized_score ?? 0) / 100) * 10).toFixed(2)),
    hip_flexion_angle: Number((output.smallest_loading_min_hip_flexion ?? 0).toFixed(2)),
    knee_flexion_score: Number((((output.knee_normalized_score ?? 0) / 100) * 10).toFixed(2)),
    knee_flexion_angle: Number((output.smallest_loading_min_knee_flexion ?? 0).toFixed(2)),
    swing_velocity_score: Number((output.angular_velocity_score ?? 0).toFixed(2)),
    swing_velocity: Number((output.angular_velocity ?? 0).toFixed(2)),
    overall_feedback: output.llm_report || 'No report generated.',
    // Backend currently returns a local file path, not a browser-accessible URL.
    annotated_video_url: '',
  }
}

export default function AnalyticsPage() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [analysisData, setAnalysisData] = useState<JumpAnalysisData | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleFileSelect = async (file: File) => {
    setVideoFile(file)
    setErrorMessage(null)
    setAnalysisData(null)
    setIsAnalyzing(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(ANALYZE_ENDPOINT, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null) as { detail?: string } | null
        throw new Error(errorPayload?.detail || `Request failed with status ${res.status}`)
      }

      const payload = await res.json() as BackendUploadResponse
      setAnalysisData(toPanelData(payload))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to analyze video.'
      setErrorMessage(message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Jump<span className="text-primary">Analyze</span>
          </h1>
          <Link
            href="/"
            className="text-sm font-medium text-primary hover:underline"
          >
            Back to Landing
          </Link>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row h-[calc(100vh-57px)]">
        <div className="flex-1 p-4 border-r border-border">
          <VideoUploader
            videoFile={videoFile}
            annotatedVideoUrl={analysisData?.annotated_video_url || null}
            onFileSelect={handleFileSelect}
            isAnalyzing={isAnalyzing}
          />
        </div>

        <div className="w-full lg:w-[480px] xl:w-[520px] p-4 overflow-y-auto">
          {errorMessage && (
            <div className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-700">
              {errorMessage}
            </div>
          )}
          <AnalyticsPanel data={analysisData} />
        </div>
      </div>
    </div>
  )
}
