import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { ToastProvider, useToast } from "@/components/ui/toast";
import { routeObjects } from "@/router";

afterEach(cleanup);

function ToastButtons() {
  const { showToast } = useToast();
  return (
    <>
      <button onClick={() => showToast("First notification")}>Send first</button>
      <button onClick={() => showToast("Second notification", "error")}>Send second</button>
    </>
  );
}

it("shares a toast provider across routed components and handles consecutive notifications", () => {
  const router = createMemoryRouter([{ path: "/", element: <ToastButtons /> }]);
  render(<ToastProvider><RouterProvider router={router} /></ToastProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Send first" }));
  fireEvent.click(screen.getByRole("button", { name: "Send second" }));
  expect(screen.getByText("First notification")).toBeTruthy();
  expect(screen.getByText("Second notification")).toBeTruthy();
  expect(screen.getByRole("status")).toBeTruthy();
});

it("renders a safe recoverable error page instead of React Router's default page", async () => {
  const router = createMemoryRouter(routeObjects, { initialEntries: ["/this-page-does-not-exist"] });
  render(<RouterProvider router={router} />);
  expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Go to homepage" }).getAttribute("href")).toBe("/");
  expect(screen.queryByText("Unexpected Application Error!")).toBeNull();
});
