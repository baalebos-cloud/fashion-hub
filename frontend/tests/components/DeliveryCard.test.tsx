import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import type { DeliveryStatus } from "@/types/delivery";

it.each<[DeliveryStatus, string]>([
  ["assigned", "₦2,500"], ["picked_up", "₦2,500"], ["out_for_delivery", "₦2,500"], ["delivered", "₦2,500"],
  ["cancelled", "No fare"], ["failed", "No fare"],
])("a %s job shows %s", (status, shown) => {
  render(<MemoryRouter><DeliveryCard delivery={{ id: "d1", order_id: "abcdef123456", status, delivery_fee: 2500 }} detailsPath="/x" /></MemoryRouter>);
  expect(screen.getByText(shown)).toBeTruthy();
});
