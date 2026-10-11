export { middleware } from "@anthusai/papyrus/middleware";
export const config = {
  runtime: "nodejs",
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon).*)"],
};
