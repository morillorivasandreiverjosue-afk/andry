import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fondo } from "./estilos";

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame, fps, config: { damping: 200 } });
  const sub = interpolate(frame, [1 * fps, 2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const linea = interpolate(frame, [0.5 * fps, 2.5 * fps], [0, 600], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <AbsoluteFill style={fondo("#1e1b4b", "#7c3aed")}>
      <div
        style={{
          fontSize: 150,
          fontWeight: 800,
          transform: `scale(${0.8 + 0.2 * entrada})`,
          opacity: entrada,
        }}
      >
        Video de prueba
      </div>
      <div style={{ height: 8, width: linea, background: "#facc15", borderRadius: 4, margin: "30px 0" }} />
      <div style={{ fontSize: 56, opacity: sub, transform: `translateY(${(1 - sub) * 30}px)` }}>
        Editado con Remotion · 40 segundos
      </div>
    </AbsoluteFill>
  );
};
