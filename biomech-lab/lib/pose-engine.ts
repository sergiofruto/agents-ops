import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";
import type { RawLandmark } from "./landmarks";
import { MODEL_URL, WASM_URL } from "./pose-engine-config";

export type Detection = { people: RawLandmark[][]; width: number; height: number };

export interface PoseEngine {
  detectImage(image: HTMLImageElement): Detection;
  close(): void;
}

type Vision = Awaited<ReturnType<typeof FilesetResolver.forVisionTasks>>;

function createLandmarker(vision: Vision, delegate: "GPU" | "CPU") {
  return PoseLandmarker.createFromOptions(vision, {
    baseOptions: { modelAssetPath: MODEL_URL, delegate },
    runningMode: "IMAGE",
    numPoses: 2, // detect a second person so we can reject multi-person photos
  });
}

export async function createImageEngine(): Promise<PoseEngine> {
  const vision = await FilesetResolver.forVisionTasks(WASM_URL);
  let landmarker: PoseLandmarker;
  try {
    landmarker = await createLandmarker(vision, "GPU");
  } catch {
    landmarker = await createLandmarker(vision, "CPU");
  }
  return {
    detectImage(image) {
      const result = landmarker.detect(image);
      return {
        people: result.landmarks.map((person) =>
          person.map((l) => ({ x: l.x, y: l.y, z: l.z, visibility: l.visibility })),
        ),
        width: image.naturalWidth,
        height: image.naturalHeight,
      };
    },
    close: () => landmarker.close(),
  };
}
