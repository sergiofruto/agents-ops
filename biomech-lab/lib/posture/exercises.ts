import type { FindingId } from "./config";
import type { Finding } from "./findings";

export type Exercise = { name: string; steps: string[]; dosage: string };

type Entry = {
  explanation: (f: Finding) => string;
  exercises: (f: Finding) => [Exercise, Exercise, Exercise];
};

const STOP = "Stop if it hurts.";

/** The side the finding points to, defaulting to right when unknown. */
const sideOf = (f: Finding): "left" | "right" => f.side ?? "right";
const opposite = (s: "left" | "right") => (s === "left" ? "right" : "left");

const chinTucks: Exercise = {
  name: "Chin tucks",
  steps: [
    "Sit or stand tall with your eyes level.",
    "Slide your chin straight back, as if making a double chin, without tipping your head down.",
    "Hold for 3 seconds, then relax.",
  ],
  dosage: `3 sets of 10, daily. ${STOP}`,
};

export const LIBRARY: Record<FindingId, Entry> = {
  forwardHead: {
    explanation: () =>
      "When the head sits ahead of the shoulders, the muscles at the back of the neck work harder to hold it up. It is common after long hours at a desk or on a phone, and it often comes with tight chest muscles and a rounded upper back.",
    exercises: () => [
      chinTucks,
      {
        name: "Doorway chest stretch",
        steps: [
          "Stand in a doorway with your forearms on the frame, elbows at shoulder height.",
          "Step one foot forward until you feel a gentle stretch across your chest.",
          "Keep your chin tucked and breathe slowly.",
        ],
        dosage: `3 holds of 30 seconds. ${STOP}`,
      },
      {
        name: "Wall angels",
        steps: [
          "Stand with your back, head and hips against a wall, feet a little forward.",
          "Raise your arms to a goal-post shape with the backs of your hands near the wall.",
          "Slide your arms up and down slowly, keeping your head and lower back against the wall.",
        ],
        dosage: `3 sets of 8. ${STOP}`,
      },
    ],
  },

  headTilt: {
    explanation: (f) =>
      `Your head leans toward your ${sideOf(f)} shoulder. A small tilt is common and can come from habits like holding a phone between ear and shoulder, or from tighter neck muscles on one side.`,
    exercises: (f) => [
      {
        name: `Upper trapezius stretch (${opposite(sideOf(f))} side)`,
        steps: [
          "Sit tall and hold the edge of the chair with one hand.",
          `Gently tilt your ear toward your ${sideOf(f)} shoulder to stretch the ${opposite(sideOf(f))} side of your neck.`,
          "Keep your shoulders down and breathe slowly.",
        ],
        dosage: `2 holds of 30 seconds. ${STOP}`,
      },
      {
        name: `Levator scapulae stretch (${sideOf(f)} side)`,
        steps: [
          `Turn your nose toward your ${opposite(sideOf(f))} armpit.`,
          "Use that hand to gently guide your head down until you feel a stretch at the back of the neck.",
          "Keep the opposite shoulder relaxed and low.",
        ],
        dosage: `2 holds of 30 seconds. ${STOP}`,
      },
      {
        ...chinTucks,
        name: "Chin tucks with a level gaze",
        steps: [...chinTucks.steps.slice(0, 2), "Check in a mirror that your eyes stay level, then relax."],
      },
    ],
  },

  shoulderLevel: {
    explanation: (f) =>
      `Your ${sideOf(f)} shoulder sits lower than your ${opposite(sideOf(f))}. Small differences are normal, often linked to your dominant hand, carrying bags on one side, or muscle balance around the shoulder blades.`,
    exercises: (f) => [
      {
        name: `Shrugs (${sideOf(f)} side)`,
        steps: [
          `Hold a light weight in your ${sideOf(f)} hand, arm by your side.`,
          "Lift that shoulder straight up toward your ear, then lower it slowly.",
          "Keep your neck long and your head still.",
        ],
        dosage: `3 sets of 12. ${STOP}`,
      },
      {
        name: `Upper trapezius stretch (${opposite(sideOf(f))} side)`,
        steps: [
          "Sit tall and hold the edge of the chair with one hand.",
          `Tilt your ear toward your ${sideOf(f)} shoulder to stretch the ${opposite(sideOf(f))} side of your neck.`,
          "Breathe slowly and let the shoulder drop.",
        ],
        dosage: `2 holds of 30 seconds. ${STOP}`,
      },
      {
        name: `Single-arm farmer carry (${sideOf(f)} hand)`,
        steps: [
          `Hold a moderate weight in your ${sideOf(f)} hand.`,
          "Walk slowly, keeping both shoulders level and your trunk upright.",
          "Switch to a lighter weight if you start to lean.",
        ],
        dosage: `3 walks of 20 meters. ${STOP}`,
      },
    ],
  },

  trunkShift: {
    explanation: (f) =>
      `Your shoulders sit to the ${sideOf(f)} of your hips. A small shift can come from standing with more weight on one leg, or from differences in strength between the two sides of your trunk.`,
    exercises: (f) => [
      {
        name: `Side plank (${opposite(sideOf(f))} side down)`,
        steps: [
          `Lie on your ${opposite(sideOf(f))} side with your elbow under your shoulder.`,
          "Lift your hips so your body forms a straight line.",
          "Breathe steadily, then lower with control.",
        ],
        dosage: `3 holds of 20 seconds. ${STOP}`,
      },
      {
        name: "Standing side bend stretch",
        steps: [
          "Stand tall with feet hip-width apart.",
          `Reach your ${sideOf(f)} arm overhead and lean gently toward your ${opposite(sideOf(f))}.`,
          "Keep both feet grounded and hips still.",
        ],
        dosage: `2 holds of 30 seconds. ${STOP}`,
      },
      {
        name: "Single-leg balance",
        steps: [
          "Stand near a wall for support.",
          "Lift one foot and keep your shoulders level over your hips.",
          "Switch legs.",
        ],
        dosage: `3 holds of 30 seconds per leg. ${STOP}`,
      },
    ],
  },

  hipLevel: {
    explanation: (f) =>
      `Your ${sideOf(f)} hip sits lower than your ${opposite(sideOf(f))}. This can come from standing on one leg more than the other, hip muscle strength differences, or a small leg length difference.`,
    exercises: (f) => [
      {
        name: `Side-lying hip abduction (${opposite(sideOf(f))} leg)`,
        steps: [
          `Lie on your ${sideOf(f)} side with your legs straight.`,
          `Lift your top (${opposite(sideOf(f))}) leg slightly behind you, toes pointing forward.`,
          "Lower slowly without rolling your hips back.",
        ],
        dosage: `3 sets of 12. ${STOP}`,
      },
      {
        name: `Standing hip hike (${sideOf(f)} side)`,
        steps: [
          `Stand on a step with your ${sideOf(f)} foot hanging off the edge.`,
          `Lift your ${sideOf(f)} hip up using the muscles of the standing side, keeping both knees straight.`,
          "Lower slowly.",
        ],
        dosage: `3 sets of 10. ${STOP}`,
      },
      {
        name: `Quadratus lumborum stretch (${opposite(sideOf(f))} side)`,
        steps: [
          "Stand tall and cross one leg behind the other.",
          `Reach your ${opposite(sideOf(f))} arm overhead and lean gently away from it.`,
          "Breathe slowly into the side of your waist.",
        ],
        dosage: `2 holds of 30 seconds. ${STOP}`,
      },
    ],
  },

  hipsForward: {
    explanation: () =>
      "Your hips sit ahead of your ankles, so your upper body leans back to balance. This relaxed sway is common when standing for a long time, and it often comes with tight hip flexors and less active glutes and abdominals.",
    exercises: () => [
      {
        name: "Glute bridge",
        steps: [
          "Lie on your back with knees bent and feet flat.",
          "Squeeze your glutes and lift your hips until your body forms a straight line from knees to shoulders.",
          "Lower slowly.",
        ],
        dosage: `3 sets of 12. ${STOP}`,
      },
      {
        name: "Dead bug",
        steps: [
          "Lie on your back with arms toward the ceiling and knees bent at 90°.",
          "Keep your lower back gently pressed to the floor.",
          "Lower the opposite arm and leg slowly, then switch.",
        ],
        dosage: `3 sets of 8 per side. ${STOP}`,
      },
      {
        name: "Half-kneeling hip flexor stretch",
        steps: [
          "Kneel on one knee with the other foot in front.",
          "Tuck your tailbone under and shift forward until you feel a stretch at the front of the back hip.",
          "Keep your trunk upright, then switch sides.",
        ],
        dosage: `2 holds of 30 seconds per side. ${STOP}`,
      },
    ],
  },

  kneeHyperextension: {
    explanation: () =>
      "Your knee bends back past straight when you stand. Many people lock their knees this way to rest, which shifts load onto the back of the knee instead of the muscles around it.",
    exercises: () => [
      {
        name: "Soft-knee standing",
        steps: [
          "Stand in front of a mirror, side on.",
          "Unlock your knees so they are straight but not pushed back.",
          "Practice holding this position during everyday standing.",
        ],
        dosage: `5 times a day for 1 minute. ${STOP}`,
      },
      {
        name: "Band hamstring curls",
        steps: [
          "Lie on your stomach with a light band around your ankle, anchored in front of you.",
          "Bend your knee to bring your heel toward your glutes.",
          "Lower slowly.",
        ],
        dosage: `3 sets of 12 per leg. ${STOP}`,
      },
      {
        name: "Calf raises with soft knees",
        steps: [
          "Stand holding a wall with knees slightly unlocked.",
          "Rise onto your toes without letting your knees snap back.",
          "Lower slowly.",
        ],
        dosage: `3 sets of 15. ${STOP}`,
      },
    ],
  },

  heelAlignment: {
    explanation: (f) =>
      `Your ${sideOf(f)} heel tilts away from vertical when seen from behind. This is often linked to the arch of the foot rolling in or out, and footwear and foot strength both play a part.`,
    exercises: () => [
      {
        name: "Short-foot exercise",
        steps: [
          "Sit with your foot flat on the floor.",
          "Draw the ball of your foot toward your heel to lift the arch, without curling your toes.",
          "Hold for 5 seconds, then relax.",
        ],
        dosage: `3 sets of 10 per foot. ${STOP}`,
      },
      {
        name: "Single-leg calf raises",
        steps: [
          "Stand on one foot, holding a wall for balance.",
          "Rise onto your toes keeping your heel pointing straight up.",
          "Lower slowly.",
        ],
        dosage: `3 sets of 10 per leg. ${STOP}`,
      },
      {
        name: "Towel scrunches",
        steps: [
          "Sit with a small towel flat under your foot.",
          "Use your toes to pull the towel toward you.",
          "Spread it out and repeat.",
        ],
        dosage: `3 sets of 10 per foot. ${STOP}`,
      },
    ],
  },
};
