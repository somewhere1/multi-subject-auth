import client from './client';

export interface SessionResponse {
  id: string;
  device_name: string | null;
  ip_address: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
}

export async function listSessions(): Promise<SessionResponse[]> {
  const { data } = await client.get<SessionResponse[]>('/sessions/');
  return data;
}

export async function revokeSession(sessionId: string): Promise<void> {
  await client.delete(`/sessions/${sessionId}`);
}
