import { checkSpecRows } from "@/lib/check-spec";
import { container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

export function CheckSpec() {
  const rows = checkSpecRows();
  return (
    <section id="checks" aria-labelledby="checks-title" className={sectionShell}>
      <div className={`${container} py-20`}>
        <p className={label}>04 · Check spec</p>
        <h2 id="checks-title" className={sectionTitle}>
          Every rule, in the open
        </h2>
        <p className="mt-3 max-w-2xl text-fg-muted">
          Generated from the scoring code. Full credit inside the tolerance, partial credit up to
          twice the tolerance, zero beyond.
        </p>
        <div className={`${panel} mt-10 overflow-x-auto`}>
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Scoring checks per pose</caption>
            <thead className="border-b border-line font-mono text-[11px] uppercase tracking-wider text-fg-subtle">
              <tr>
                <th scope="col" className="px-4 py-3">pose</th>
                <th scope="col" className="px-4 py-3">check_id</th>
                <th scope="col" className="px-4 py-3">measures</th>
                <th scope="col" className="px-4 py-3">target</th>
                <th scope="col" className="px-4 py-3">tolerance</th>
                <th scope="col" className="px-4 py-3 text-right">weight</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={`${r.poseId}-${r.id}`}>
                  <td className="px-4 py-2.5 text-fg-muted">{r.pose}</td>
                  <td className="px-4 py-2.5 font-mono text-accent">{r.id}</td>
                  <td className="px-4 py-2.5 text-fg-strong">{r.label}</td>
                  <td className="px-4 py-2.5 font-mono">{r.target}</td>
                  <td className="px-4 py-2.5 font-mono">{r.tolerance}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{r.weight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
