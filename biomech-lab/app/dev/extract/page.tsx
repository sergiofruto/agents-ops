import { notFound } from "next/navigation";
import { Extractor } from "@/components/dev/Extractor";

export default function ExtractPage() {
  if (process.env.NODE_ENV !== "development") notFound();
  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <h1 className="text-2xl font-bold">Fixture extractor (dev only)</h1>
      <Extractor />
    </main>
  );
}
