import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fondo } from "./estilos";

const pasos = ["✂️  Cortar clips", "🎵  Añadir música", "🔤  Poner textos", "✨  Transiciones", "📤  Exportar"];

export const Lista: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ ...fondo("#7f1d1d", "#ea580c"), alignItems: "flex-start", paddingLeft: 300 }}>
      <div style={{ fontSize: 96, fontWeight: 800, marginBottom: 50 }}>Qué puedes hacer</div>
      {pasos.map((paso, i) => {
        const s = spring({ frame: frame - fps * (0.6 + i * 1.2), fps, config: { damping: 200 } });
        return (
          <div
            key={paso}
            style={{
              fontSize: 64,
              margin: "14px 0",
              opacity: s,
              transform: `translateX(${(1 - s) * -120}px)`,
            }}
          >
            {paso}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
