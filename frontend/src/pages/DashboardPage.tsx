import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getMe } from '../api/auth';
import SessionList from '../components/SessionList';
import CredentialManager from '../components/CredentialManager';
import MfaSetup from '../components/MfaSetup';

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  member: { label: 'Member', color: 'bg-blue-100 text-blue-700' },
  community_staff: { label: 'Community Staff', color: 'bg-green-100 text-green-700' },
  platform_staff: { label: 'Platform Staff', color: 'bg-purple-100 text-purple-700' },
};

export default function DashboardPage() {
  const { subject, logout, setSubject } = useAuth();
  const navigate = useNavigate();
  const [mfaEnabled, setMfaEnabled] = useState(subject?.mfa_enabled ?? false);

  const handleMfaStatusChange = useCallback(async () => {
    const updated = await getMe();
    setMfaEnabled(updated.mfa_enabled);
    setSubject(updated);
  }, [setSubject]);

  if (!subject) return null;

  const typeInfo = TYPE_LABELS[subject.subject_type] || { label: subject.subject_type, color: 'bg-gray-100 text-gray-700' };

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Welcome, {subject.display_name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${typeInfo.color}`}>
                  {typeInfo.label}
                </span>
                <span className="text-sm text-gray-500">{subject.email}</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Account Info */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Account Info</h3>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-gray-500">ID</dt>
              <dd className="text-gray-800 font-mono text-xs mt-0.5">{subject.id}</dd>
            </div>
            <div>
              <dt className="text-gray-500">MFA</dt>
              <dd className="text-gray-800 mt-0.5">{mfaEnabled ? 'Enabled' : 'Disabled'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Created</dt>
              <dd className="text-gray-800 mt-0.5">{new Date(subject.created_at).toLocaleDateString()}</dd>
            </div>
          </dl>
        </div>

        {/* MFA Setup */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <MfaSetup mfaEnabled={mfaEnabled} onStatusChange={handleMfaStatusChange} />
        </div>

        {/* Credentials */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <CredentialManager />
        </div>

        {/* Sessions */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <SessionList />
        </div>
      </div>
    </div>
  );
}
