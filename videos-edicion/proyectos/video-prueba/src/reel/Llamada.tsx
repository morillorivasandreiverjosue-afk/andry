import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// Botón final "SÍGUEME" que rebota y "late"
export const Llamada: React.FC<{ desde: number }> = ({ desde }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - desde * fps;
  if (f < 0) return null;
  const entrada = spring({ frame: f, fps, config: { damping: 9 } });
  const latido = 1 + 0.05 * Math.sin(f / 4);
  const brillo = interpolate(f % 45, [0, 22, 45], [0, 1, 0]);

  return (
    <div
      style={{
        position: "absolute",
        top: 170,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        transform: `translateY(${(1 - entrada) * -300}px) scale(${latido})`,
      }}
    >
      <div
        style={{
          fontFamily: "Montserrat",
          fontWeight: 900,
          fontSize: 64,
          color: "white",
          padding: "26px 56px",
          borderRadius: 999,
          background: "linear-gradient(90deg, #ff0050, #ff7a00)",
          boxShadow: `0 0 ${30 + 40 * brillo}px rgba(255,0,80,0.9), 0 12px 0 #8a0030`,
        }}
      >
        🔔 SÍGUEME PARA MÁS
      </div>
    </div>
  );
};
