import type { Body } from "@/lib/body";
import type { Joint, Side } from "@/lib/landmarks";

export type PoseId = "warrior2" | "tree" | "downdog";
export type Mode = "photo" | "live";
export type Roles = Record<string, Side>;

type CheckBase = {
  id: string;
  label: string;
  cue: string;
  unit: "deg" | "ratio";
  weight: number;
  /** Physical bounds of the measured value; used by the coach API to validate input. */
  bounds: [number, number];
  required: (roles: Roles) => Joint[];
};

type FrameSource = { source: "frame"; measure: (body: Body, roles: Roles) => number };
type WindowSource = { source: "window" };

type RangeTarget = { kind: "range"; target: number; tol: number };
type MinTarget = { kind: "min"; min: number };

export type CheckDef = CheckBase & (FrameSource | WindowSource) & (RangeTarget | MinTarget);

export type PoseDef = {
  id: PoseId;
  label: string;
  view: "front" | "side";
  assignRoles: (body: Body) => Roles;
  checks: CheckDef[];
};
