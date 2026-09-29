import { PhotoLab } from "@/components/PhotoLab";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl space-y-8 px-4 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Biomech Lab</h1>
        <p className="text-neutral-300">
          Recognizes Warrior II, Tree and Downward Dog, then scores your form from joint angles
          measured in your browser.
        </p>
        <p className="text-sm text-neutral-400">
          Images and video stay on your device. Only anonymous measurement results are sent when
          you ask for coaching.
        </p>
      </header>
      <PhotoLab />
    </main>
  );
}
