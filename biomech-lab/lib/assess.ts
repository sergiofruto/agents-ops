import { toBody } from "./body";
import { classify } from "./classify";
import type { RawLandmark } from "./landmarks";
import { readinessMessages } from "./messages";
import { POSES, type PoseId } from "./poses";
import { assessReadiness, type AssessmentReadiness } from "./readiness";
import { measureFrame, scoreMeasurements, type Measurement, type ScoreResult } from "./score";

export type Assessment =
  | { kind: "no_person" }
  | { kind: "multiple_people" }
  | { kind: "unknown_pose" }
  | {
      kind: "not_ready";
      pose: PoseId;
      confidence: number;
      readiness: AssessmentReadiness;
      messages: string[];
    }
  | {
      kind: "scored";
      pose: PoseId;
      confidence: number;
      readiness: AssessmentReadiness;
      measurements: Measurement[];
      result: ScoreResult;
    };

/** Photo/sample path: detect → people check → classify → readiness → single-frame score. */
export function assessPhoto(people: RawLandmark[][], width: number, height: number): Assessment {
  if (people.length === 0) return { kind: "no_person" };
  if (people.length > 1) return { kind: "multiple_people" };

  const body = toBody(people[0], width, height);
  const { pose: id, confidence } = classify(body);
  if (id === "unknown") return { kind: "unknown_pose" };

  const pose = POSES[id];
  const readiness = assessReadiness({ peopleCount: 1, body, pose, mode: "photo" });
  if (!readiness.canScore) {
    return { kind: "not_ready", pose: id, confidence, readiness, messages: readinessMessages(readiness, pose) };
  }

  const measurements = measureFrame(pose, body, "photo");
  return {
    kind: "scored",
    pose: id,
    confidence,
    readiness,
    measurements,
    result: scoreMeasurements(pose, measurements, "photo"),
  };
}
