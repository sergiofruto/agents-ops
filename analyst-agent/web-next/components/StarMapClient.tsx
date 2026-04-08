"use client";

import dynamic from "next/dynamic";
import type { SkyData } from "@/lib/types";

const StarMap = dynamic(() => import("./StarMap"), { ssr: false });

export default function StarMapClient({ sky }: { sky: SkyData }) {
  return <StarMap sky={sky} width={420} height={420} />;
}
