export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4">
      <div className="mb-3 text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
        {title}
      </div>
      {children}
    </div>
  );
}
