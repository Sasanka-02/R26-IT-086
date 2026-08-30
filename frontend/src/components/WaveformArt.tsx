interface WaveformArtProps {
  className?: string;
  animated?: boolean;
}

/**
 * The hero/section-divider signature: a hand-feeling waveform arc.
 * Pure SVG, no external image dependency, ties directly to "capturing
 * and listening to speech" rather than being generic decoration.
 */
export default function WaveformArt({ className = "", animated = true }: WaveformArtProps) {
  const bars = [
    14, 22, 34, 48, 62, 74, 88, 70, 56, 40, 30, 44, 60, 78, 92, 76, 58, 42,
    28, 18, 30, 46, 64, 50, 36, 24,
  ];
  const width = bars.length * 10;

  return (
    <svg
      viewBox={`0 0 ${width} 100`}
      className={className}
      preserveAspectRatio="none"
      role="presentation"
    >
      {bars.map((h, i) => (
        <rect
          key={i}
          x={i * 10 + 2}
          y={(100 - h) / 2}
          width={5}
          height={h}
          rx={2.5}
          className={animated ? "fill-teal-500/70" : "fill-teal-500/40"}
          style={
            animated
              ? {
                  animation: `waveform-pulse 1.8s ease-in-out ${(i % 6) * 0.12}s infinite`,
                  transformOrigin: "center",
                }
              : undefined
          }
        />
      ))}
      <style>{`
        @keyframes waveform-pulse {
          0%, 100% { transform: scaleY(0.55); }
          50% { transform: scaleY(1); }
        }
        @media (prefers-reduced-motion: reduce) {
          rect { animation: none !important; }
        }
      `}</style>
    </svg>
  );
}