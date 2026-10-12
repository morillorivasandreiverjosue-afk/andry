import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { useVideoConfig } from "remotion";
import { Contador } from "./escenas/Contador";
import { Final } from "./escenas/Final";
import { Formas } from "./escenas/Formas";
import { Intro } from "./escenas/Intro";
import { Lista } from "./escenas/Lista";

// 5 escenas (8+9+9+9+7 s = 42 s) menos 4 transiciones de 0,5 s = 40 s
export const VideoPrueba: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <TransitionSeries>
      <TransitionSeries.Sequence name="Intro" durationInFrames={8 * fps} premountFor={fps}>
        <Intro />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 0.5 * fps })} />
      <TransitionSeries.Sequence name="Formas" durationInFrames={9 * fps} premountFor={fps}>
        <Formas />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: 0.5 * fps })}
      />
      <TransitionSeries.Sequence name="Contador" durationInFrames={9 * fps} premountFor={fps}>
        <Contador />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={wipe({ direction: "from-left" })}
        timing={linearTiming({ durationInFrames: 0.5 * fps })}
      />
      <TransitionSeries.Sequence name="Lista" durationInFrames={9 * fps} premountFor={fps}>
        <Lista />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 0.5 * fps })} />
      <TransitionSeries.Sequence name="Final" durationInFrames={7 * fps} premountFor={fps}>
        <Final />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
