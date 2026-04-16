import { useState, useEffect } from 'react';
import { listSessions, revokeSession, type SessionResponse } from '../api/sessions';

export default function SessionList() {
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchSessions() {
    setLoading(true);
    try {
      const data = await listSessions();
      setSessions(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchSessions(); }, []);

  async function handleRevoke(id: string) {
    await revokeSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  }

  if (loading) return <div className="text-gray-500 text-sm">Loading sessions...</div>;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-800">Active Sessions</h3>
      {sessions.length === 0 ? (
        <p className="text-gray-500 text-sm">No active sessions</p>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800 text-sm">
                    {session.device_name || 'Unknown Device'}
                  </span>
                  {session.is_current && (
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                      Current
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {session.ip_address} &middot; Last active: {new Date(session.last_active_at).toLocaleString()}
                </div>
              </div>
              {!session.is_current && (
                <button
                  onClick={() => handleRevoke(session.id)}
                  className="px-3 py-1 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
