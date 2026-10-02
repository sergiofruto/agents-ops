/** Keep in sync with package.json — enforced by test/pose-engine-config.test.ts. */
export const MEDIAPIPE_VERSION = "1.0.1";

export const WASM_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/wasm`;

/** Full model: better accuracy for still photos. Day 2 may use the lite model for live video. */
export const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task";
