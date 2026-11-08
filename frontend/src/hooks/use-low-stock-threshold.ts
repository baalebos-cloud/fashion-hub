import { useCallback, useEffect, useRef, useState } from "react";
import { vendorsApi } from "@/api/vendors.api";
import { DEFAULT_LOW_STOCK_THRESHOLD } from "@/constants/order-status";

/** The vendor's chosen low-stock level, and a way to change it. Falls back to the default. */
export function useLowStockThreshold() {
  const [threshold, setThreshold] = useState(DEFAULT_LOW_STOCK_THRESHOLD);
  // Once the vendor saves, a slower first load must not put the old value back.
  const saved = useRef(false);
  useEffect(() => {
    let active = true;
    vendorsApi.mine()
      .then((vendor) => {
        if (active && !saved.current && typeof vendor?.low_stock_threshold === "number") setThreshold(vendor.low_stock_threshold);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);
  const save = useCallback(async (value: number) => {
    const vendor = await vendorsApi.setStockAlert(value);
    saved.current = true;
    setThreshold(vendor.low_stock_threshold ?? value);
  }, []);
  return { threshold, save };
}
