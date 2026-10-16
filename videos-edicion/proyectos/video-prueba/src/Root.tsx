import { Composition } from "remotion";
import { ReelInternet } from "./reel/ReelInternet";
import { VideoPrueba } from "./VideoPrueba";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ReelInternet"
        component={ReelInternet}
        durationInFrames={2160}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="VideoPrueba"
        component={VideoPrueba}
        durationInFrames={1200}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
