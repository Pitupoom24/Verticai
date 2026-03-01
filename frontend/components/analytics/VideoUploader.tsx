import { useCallback, useRef } from 'react'

interface VideoUploaderProps {
  videoFile: File | null
  annotatedVideoUrl: string | null
  onFileSelect: (file: File) => void
  isAnalyzing: boolean
}

export default function VideoUploader({
  videoFile,
  annotatedVideoUrl,
  onFileSelect,
  isAnalyzing,
}: VideoUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file && file.type.startsWith('video/')) {
        onFileSelect(file)
      }
    },
    [onFileSelect]
  )

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onFileSelect(file)
  }

  if (annotatedVideoUrl) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center bg-foreground/[0.02] rounded-lg overflow-hidden">
          <video
            src={annotatedVideoUrl}
            controls
            className="w-full h-full object-contain max-h-[70vh]"
          />
        </div>
      </div>
    )
  }

  if (videoFile) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center bg-foreground/[0.02] rounded-lg overflow-hidden">
          <video
            src={URL.createObjectURL(videoFile)}
            controls
            className="w-full h-full object-contain max-h-[70vh]"
          />
        </div>
        {isAnalyzing && (
          <div className="mt-4 flex items-center gap-3 text-muted-foreground">
            <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-medium">Analyzing your jump...</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className="flex flex-col items-center justify-center h-full min-h-[400px] border-2 border-dashed border-border rounded-xl cursor-pointer hover:border-primary/50 hover:bg-primary/[0.02] transition-all duration-200"
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mb-3">
        <span className="text-2xl font-bold text-primary" aria-hidden="true">↑</span>
      </div>
      <p className="text-base font-semibold text-foreground mb-1">Upload your jump video</p>
      <p className="text-sm text-muted-foreground">Drag & drop or click to browse</p>
      <p className="text-xs text-muted-foreground mt-2">MP4, MOV, AVI supported</p>
    </div>
  )
}
