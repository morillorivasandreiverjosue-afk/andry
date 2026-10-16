import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import voz from "./voz.json";

const PALABRAS_POR_BLOQUE = 3;

// En la portada (0-5 s) el título del video llega muy abajo: ahí los subtítulos bajan
const posicion = (seg: number) => (seg < 5 ? 1600 : 1420);

// Subtítulos estilo TikTok: bloques de 3 palabras, la palabra que suena en amarillo
export const Subtitulos: React.FC<{ hasta: number }> = ({ hasta }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seg = frame / fps;
  if (seg >= hasta) return null;

  const linea = voz.find((l) => seg >= l.inicio && seg < l.inicio + l.duracion + 0.15);
  if (!linea) return null;

  const idx = Math.max(0, linea.palabras.findIndex((p) => seg < p.hasta));
  const inicioBloque = Math.floor(idx / PALABRAS_POR_BLOQUE) * PALABRAS_POR_BLOQUE;
  const bloque = linea.palabras.slice(inicioBloque, inicioBloque + PALABRAS_POR_BLOQUE);
  const entrada = spring({ frame: frame - Math.round(bloque[0].desde * fps), fps, config: { damping: 12, stiffness: 200 } });

  return (
    <div
      style={{
        position: "absolute",
        top: posicion(seg),
        left: 70,
        right: 70,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "0 44px",
        transform: `scale(${0.6 + 0.4 * entrada}) rotate(${(1 - entrada) * -4}deg)`,
      }}
    >
      {bloque.map((p, i) => {
        const activa = inicioBloque + i === idx;
        const pop = activa ? spring({ frame: frame - Math.round(p.desde * fps), fps, config: { damping: 10, stiffness: 300 } }) : 0;
        return (
          <span
            key={`${inicioBloque}-${i}`}
            style={{
              fontFamily: "Anton",
              fontSize: 104,
              lineHeight: 1.15,
              textTransform: "uppercase",
              color: activa ? "#FFE600" : "white",
              WebkitTextStroke: "12px black",
              paintOrder: "stroke fill",
              textShadow: "0 8px 0 rgba(0,0,0,0.6), 0 0 30px rgba(0,0,0,0.5)",
              display: "inline-block",
              transform: `translateY(${-14 * pop}px) scale(${1 + 0.06 * pop})`,
            }}
          >
            {p.texto}
          </span>
        );
      })}
    </div>
  );
};
