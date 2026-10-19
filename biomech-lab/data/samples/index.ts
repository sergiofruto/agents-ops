import type { RawLandmark } from "@/lib/landmarks";
import downdog from "./downdog.json";
import tree from "./tree.json";
import warrior2 from "./warrior2.json";

export type LandmarkFile = { sample: string; width: number; height: number; people: RawLandmark[][] };

/** MediaPipe landmark extractions of the published sample photos (see /dev/extract). */
export const LANDMARK_FILES: Record<string, LandmarkFile> = { warrior2, tree, downdog };
