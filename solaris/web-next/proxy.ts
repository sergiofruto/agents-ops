import { NextResponse, type NextRequest } from "next/server";
import { isValidCookie, COOKIE_NAME } from "@/lib/auth";

// Next 16 renames `middleware` → `proxy`. Same gate semantics.
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/_next") ||
      pathname === "/favicon.ico") {
    return NextResponse.next();
  }
  if (isValidCookie(request.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.next();
  }
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
