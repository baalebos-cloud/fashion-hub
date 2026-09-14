export interface Review {
  id: string;
  order_id: string;
  comment?: string | null;
  score?: number;
  created_at?: string;
}
