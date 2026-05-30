"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { checkPassword, makeSessionCookie } from "@/lib/auth";

export async function login(formData: FormData) {
  const pw = String(formData.get("password") ?? "");
  if (!checkPassword(pw)) redirect("/login?error=1");
  const c = makeSessionCookie();
  (await cookies()).set(c.name, c.value, {
    httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 30,
  });
  redirect("/");
}
