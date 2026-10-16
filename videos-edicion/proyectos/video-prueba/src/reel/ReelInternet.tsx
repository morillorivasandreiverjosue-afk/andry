import { Audio, Video } from "@remotion/media";
import { AbsoluteFill, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import "./fuentes";
import { Llamada } from "./Llamada";
import { CORTES, EFECTOS, GOLPES, INICIO_CTA } from "./momentos";
import { Subtitulos } from "./Subtitulos";
import voz from "./voz.json";

const hablando = (seg: number) => voz.some((l) => seg >= l.inicio - 0.1 && seg < l.inicio + l.duracion + 0.1);

export const ReelInternet: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const seg = frame / fps;

  // Zoom lento dentro de cada escena + golpe de zoom en cada corte e impacto
  const ultimoCorte = [0, ...CORTES].filter((c) => c <= seg).pop() ?? 0;
  const zoomLento = interpolate(seg - ultimoCorte, [0, 7], [1.0, 1.06], { extrapolateRight: "clamp" });
  const impacto = [...CORTES, ...GOLPES].reduce((acc, s) => {
    const f = frame - Math.round(s * fps);
    if (f < 0 || f > fps) return acc;
    return acc + 0.12 * (1 - spring({ frame: f, fps, config: { damping: 14, stiffness: 180 } }));
  }, 0);

  // Sacudida en los golpes
  const sacudida = GOLPES.reduce((acc, s) => {
    const f = frame - Math.round(s * fps);
    if (f < 0 || f > 12) return acc;
    return acc + (12 - f) * 1.6;
  }, 0);
  const dx = Math.sin(frame * 2.7) * sacudida;
  const dy = Math.cos(frame * 3.3) * sacudida;

  // Flash blanco en los cortes y destello rojo en los golpes
  const destello = (momentos: number[], dur: number, max: number) =>
    Math.max(
      0,
      ...momentos.map((s) => {
        const f = frame - s * fps;
        return f < 0 ? 0 : interpolate(f, [0, dur], [max, 0], { extrapolateRight: "clamp" });
      }),
    );
  const flash = destello(CORTES, 7, 0.7);
  const rojo = destello(GOLPES, 8, 0.18);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${zoomLento + impacto})` }}>
        <Video
          src={staticFile("reel/original.mp4")}
          objectFit="cover"
          style={{ width: "100%", height: "100%" }}
          // La música original baja cuando habla la voz
          volume={(f) => (hablando(f / fps) ? 0.2 : 0.55)}
        />
      </AbsoluteFill>

      {/* Viñeta para que resalten los textos */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
      <AbsoluteFill style={{ backgroundColor: "white", opacity: flash }} />
      <AbsoluteFill style={{ backgroundColor: "#ff1744", opacity: rojo, mixBlendMode: "screen" }} />

      <Subtitulos hasta={INICIO_CTA - 2} />
      <Llamada desde={INICIO_CTA} />

      {/* Barra de progreso arriba */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 12,
          width: `${(frame / durationInFrames) * 100}%`,
          background: "linear-gradient(90deg, #00e5ff, #ff0050)",
          boxShadow: "0 0 20px #00e5ff",
        }}
      />

      {voz.map((l) => (
        <Sequence key={l.archivo} name={`Voz ${l.archivo}`} from={Math.round(l.inicio * fps)} premountFor={fps}>
          <Audio src={staticFile(l.archivo)} volume={1} />
        </Sequence>
      ))}
      {EFECTOS.map((e, i) => (
        <Sequence key={i} name={`SFX ${e.sonido}`} from={Math.round(e.seg * fps)} premountFor={fps}>
          <Audio src={staticFile(`reel/${e.sonido}.wav`)} volume={e.volumen} />
        </Sequence>
      ))}
      {CORTES.map((s) => (
        <Sequence key={`w${s}`} name="SFX whoosh" from={Math.round((s - 0.3) * fps)} premountFor={fps}>
          <Audio src={staticFile("reel/whoosh.wav")} volume={0.6} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
