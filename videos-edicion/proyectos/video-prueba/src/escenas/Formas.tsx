import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fondo } from "./estilos";

const colores = ["#f43f5e", "#f59e0b", "#10b981", "#3b82f6", "#a855f7"];

export const Formas: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titulo = spring({ frame, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={fondo("#0f172a", "#1e3a8a")}>
      <div style={{ position: "absolute", top: 120, fontSize: 96, fontWeight: 800, opacity: titulo }}>
        Animaciones
      </div>
      <div style={{ display: "flex", gap: 60, marginTop: 120 }}>
        {colores.map((color, i) => {
          const s = spring({ frame: frame - 10 - i * 6, fps, config: { damping: 12 } });
          const giro = interpolate(frame, [0, 9 * fps], [0, 360 * (i % 2 === 0 ? 1 : -1)]);
          const flota = Math.sin((frame + i * 12) / 12) * 30;
          return (
            <div
              key={color}
              style={{
                width: 180,
                height: 180,
                background: color,
                borderRadius: i % 2 === 0 ? 90 : 32,
                transform: `translateY(${flota}px) scale(${s}) rotate(${giro}deg)`,
                boxShadow: "0 20px 50px rgba(0,0,0,0.4)",
              }}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
