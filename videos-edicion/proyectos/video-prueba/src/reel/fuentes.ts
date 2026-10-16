import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

loadFont({ family: "Anton", url: staticFile("fonts/Anton.woff2") });
loadFont({ family: "Montserrat", url: staticFile("fonts/Montserrat-Black.woff2"), weight: "900" });
