import { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  analyserNode: AnalyserNode | null;
  isRecording: boolean;
  height?: number;
}

/**
 * Renders a live waveform. Keeps requestAnimationFrame running even when
 * amplitude is zero (silent stuttering block) so the UI never appears
 * frozen — this is a clinical requirement, not a cosmetic one.
 */
export default function AudioVisualizer({
  analyserNode,
  isRecording,
  height = 120,
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dataArray = analyserNode
      ? new Uint8Array(analyserNode.fftSize)
      : new Uint8Array(0);

    const draw = () => {
      const width = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, width, h);

      ctx.fillStyle = "#1E1E26";
      ctx.fillRect(0, 0, width, h);

      if (analyserNode && isRecording) {
        analyserNode.getByteTimeDomainData(dataArray);
      } else {
        dataArray.fill(128);
      }

      ctx.lineWidth = 2;
      ctx.strokeStyle = isRecording ? "#A8DED6" : "#6B6B7B";
      ctx.beginPath();

      const sliceWidth = width / dataArray.length;
      let x = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * h) / 2;
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        x += sliceWidth;
      }
      ctx.lineTo(width, h / 2);
      ctx.stroke();

      animationRef.current = requestAnimationFrame(draw);
    };

    animationRef.current = requestAnimationFrame(draw);

    return () => {
      if (animationRef.current !== null) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [analyserNode, isRecording]);

  return (
    <canvas
      ref={canvasRef}
      width={640}
      height={height}
      className="w-full rounded-lg border border-teal-100 bg-paper"
      role="img"
      aria-label={isRecording ? "Live microphone waveform" : "Microphone idle"}
    />
  );
}
