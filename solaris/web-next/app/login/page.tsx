import { login } from "./actions";

export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center bg-black">
      <form action={login} className="w-72 space-y-3 rounded-lg border border-neutral-800 p-6">
        <h1 className="text-lg font-medium text-neutral-200">Solaris</h1>
        <input type="password" name="password" placeholder="Password" autoFocus
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100" />
        {error && <p className="text-xs text-red-400">Wrong password.</p>}
        <button className="w-full rounded bg-neutral-200 py-2 text-sm font-medium text-black">Enter</button>
      </form>
    </main>
  );
}
