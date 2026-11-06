import { apiClient } from "@/lib/api/client";

export interface ActivityEntry {
  id: string;
  at: string;
  event: string;
  user_id: string | null;
  user_name: string | null;
  user_email: string | null;
  role: string | null;
  method: string | null;
  path: string | null;
  status_code: number | null;
  ip_address: string | null;
  device_id: string | null;
  user_agent: string | null;
  details: Record<string, unknown>;
}

export interface ActivitySummary {
  active_now: number;
  sign_ins_24h: number;
  failed_sign_ins_24h: number;
  admin_sign_ins_24h: number;
  distinct_ips_24h: number;
  top_failed_ips: { ip_address: string; attempts: number }[];
  retention_days: number;
}

export interface FootprintItem { value: string; first_seen: string; last_seen: string; events: number }
export interface Footprint {
  user: { id: string; name: string; email: string; role: string; is_active: boolean };
  ips: FootprintItem[];
  devices: FootprintItem[];
}

export interface ActivityFilters { event?: string; email?: string; ip?: string; device_id?: string; user_id?: string; before?: string }

export interface AuditEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  actor_email: string | null;
  ip_address: string | null;
  created_at: string;
}

export const adminSecurityApi = {
  async activity(filters: ActivityFilters): Promise<ActivityEntry[]> {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    return (await apiClient.get<ActivityEntry[]>("/admin/activity", { params })).data;
  },
  async summary(): Promise<ActivitySummary> {
    return (await apiClient.get<ActivitySummary>("/admin/activity/summary")).data;
  },
  async footprint(userId: string): Promise<Footprint> {
    return (await apiClient.get<Footprint>(`/admin/users/${userId}/footprint`)).data;
  },
  async auditLogs(): Promise<AuditEntry[]> {
    return (await apiClient.get<AuditEntry[]>("/admin/audit-logs")).data;
  },
};
