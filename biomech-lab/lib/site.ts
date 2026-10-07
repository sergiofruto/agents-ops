export const SITE_URL = "https://biomech-lab.vercel.app";

export const LINKS = {
  github: "https://github.com/sergiofruto/agents-ops/tree/main/biomech-lab",
  linkedin: "https://www.linkedin.com/in/sergio-gabriel-fruto/",
} as const;

/** Light artwork is inverted + hue-rotated so it reads on the dark theme. */
export const HERO_IMAGE = {
  src: "/hero-image-temp.png",
  width: 690,
  height: 440,
  alt: "Illustration of a person in Warrior II with a skeleton overlay and joint-angle annotations",
  invertOnDark: true,
} as const;

export const APP_VERSION = "v1.1";

export const NAV_LINKS = [
  { href: "/#analyze", label: "analyze" },
  { href: "/reports", label: "reports" },
  { href: "/#pipeline", label: "pipeline" },
  { href: "/#checks", label: "checks" },
  { href: "/#privacy", label: "privacy" },
] as const;
