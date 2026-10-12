import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fondo } from "./estilos";

export const Final: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 10 } });
  const salida = interpolate(frame, [durationInFrames - fps, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ ...fondo("#111827", "#4c1d95"), opacity: salida }}>
      <div style={{ fontSize: 180, transform: `scale(${s})` }}>🎬</div>
      <div style={{ fontSize: 120, fontWeight: 800, marginTop: 20 }}>¡Funciona!</div>
      <div style={{ fontSize: 52, marginTop: 20, opacity: 0.85 }}>Fin del video de prueba</div>
    </AbsoluteFill>
  );
};
