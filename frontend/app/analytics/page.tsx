'use client'

import Link from 'next/link'
import { useState } from 'react'
import VideoUploader from '@/components/analytics/VideoUploader'
import AnalyticsPanel, { type JumpAnalysisData } from '@/components/analytics/AnalyticsPanel'

const MOCK_DATA: JumpAnalysisData = {
  total_score: 71,
  jump_height: 42,
  hip_flexion_score: 6,
  hip_flexion_angle: 105,
  knee_flexion_score: 4,
  knee_flexion_angle: 78,
  swing_velocity_score: 8,
  swing_velocity: 165,
  overall_feedback:
    'Good jump height with strong arm swing. Focus on increasing knee flexion depth and maintaining a more upright hip angle during takeoff for improved power transfer.',
  annotated_video_url: '',
}

export default function AnalyticsPage() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [analysisData, setAnalysisData] = useState<JumpAnalysisData | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleFileSelect = (file: File) => {
    setVideoFile(file)
    setIsAnalyzing(true)

    // Simulate API call – replace with backend analysis call.
    setTimeout(() => {
      setAnalysisData(MOCK_DATA)
      setIsAnalyzing(false)
    }, 2500)
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
          <AnalyticsPanel data={analysisData} />
        </div>
      </div>
    </div>
  )
}
