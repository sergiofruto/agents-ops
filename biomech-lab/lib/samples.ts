import type { PoseId } from "./poses";

export const SAMPLES: readonly { id: PoseId; src: string; label: string }[] = [
  { id: "warrior2", src: "/samples/warrior2.jpg", label: "Warrior II" },
  { id: "tree", src: "/samples/tree.jpg", label: "Tree" },
  { id: "downdog", src: "/samples/downdog.jpg", label: "Downward Dog" },
];
