import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fondo } from "./estilos";

export const Contador: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progreso = interpolate(frame, [0.5 * fps, 7 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  return (
    <AbsoluteFill style={fondo("#064e3b", "#0d9488")}>
      <div style={{ fontSize: 72, fontWeight: 700, marginBottom: 20 }}>Cargando ideas…</div>
      <div style={{ fontSize: 260, fontWeight: 900, fontVariantNumeric: "tabular-nums" }}>
        {Math.round(progreso * 100)}%
      </div>
      <div style={{ width: 1200, height: 40, background: "rgba(255,255,255,0.2)", borderRadius: 20, overflow: "hidden" }}>
        <div style={{ width: `${progreso * 100}%`, height: "100%", background: "#facc15", borderRadius: 20 }} />
      </div>
    </AbsoluteFill>
  );
};
