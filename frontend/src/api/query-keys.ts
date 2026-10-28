export const orderKeys = {
  all: ["orders"] as const,
  detail: (id: string) => ["orders", "detail", id] as const,
  list: (role: string) => ["orders", "list", role] as const,
};
export const measurementKeys = {
  all: ["measurements"] as const,
  user: (id: string) => ["measurements", "user", id] as const,
};
export const inventoryKeys = {
  all: ["inventory"] as const,
  vendor: (id: string) => ["inventory", "vendor", id] as const,
};
