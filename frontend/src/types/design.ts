export interface Design {
  id: string;
  title: string;
  description?: string | null;
  base_price: number;
  is_published: boolean;
}
