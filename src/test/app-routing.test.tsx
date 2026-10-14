import { matchRoutes } from "react-router";
import { describe, expect, it } from "vitest";
import { routes } from "@/router";

// Match routes without rendering: pages may need a network the test run lacks.
describe("App routing", () => {
  it.each([
    ["/", "home"],
    ["/auth", "sign-in"],
    ["/signup", "sign-up"],
    ["/app", "app"],
  ])("matches %s to its intended page", (path, routeId) => {
    expect(matchRoutes(routes, path)?.at(-1)?.route.id).toBe(routeId);
  });

  it("puts /app behind the auth guard", () => {
    const ids = matchRoutes(routes, "/app")?.map((m) => m.route.id);
    expect(ids).toEqual(["root", "authenticated", "app"]);
  });

  it("falls back to not found for unknown paths", () => {
    expect(matchRoutes(routes, "/nope")?.at(-1)?.route.id).toBe("not-found");
  });
});
