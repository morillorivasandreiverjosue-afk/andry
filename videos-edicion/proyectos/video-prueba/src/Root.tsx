import { Composition } from "remotion";
import { VideoPrueba } from "./VideoPrueba";

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
